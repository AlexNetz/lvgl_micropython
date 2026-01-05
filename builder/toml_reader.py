import os
import time

try:
    import toml
except ImportError:
    raise RuntimeError(
        'The toml library is needed to use this feature.\n'
        'Please run "pip3 install toml" and then restart your build'
    )

used_imports = []
global_variable_names = []
exceptions = ['try', 'except', 'else', 'finally']
global_imports = []
global_constants = []
used_constants = []

class TOMLMeta(type):

    def __call__(cls, name, parent=None, **kwargs):        
        
        if name and 'exception' in name:        
            exc = TOMLException(name, None, **kwargs)
            return exc      
        if name and 'conditional' in name:
            ret = TOMLConditional(name, None, **kwargs)
            return ret
        children = {}
        for key, value in list(kwargs.items()):
            if isinstance(value, dict):
                children[key] = value
                del kwargs[key]

        instance = super().__call__(name, parent=parent, **kwargs)

        for child_name, child_data in children.items():
            child = TOMLObject(child_name, parent=instance, **child_data)
            instance.add_child(child) 
        
        return instance
    

class TOMLObject(metaclass=TOMLMeta):

    def __init__(self, name, parent=None, **kwargs):
        if parent is not None and parent.name == 'MCU':
            self.build_args = kwargs
            self.mcu = name

            paren = parent.parent
            while paren.parent is not None:
                paren = parent.parent

            paren.mcu_obj = TOMLmcu(self)
        else:
            self.mcu = None

        self.mcu_obj = None
        self.name = name
        self.parent = parent
        self.__kwargs = kwargs
        self.__children = []
        self.imports = []

    def add_child(self, child):
        if child.name != 'MCU':
            self.__children.append(child)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if item in self.__kwargs:
            return self.__kwargs[item]

        raise AttributeError(item)

    @property
    def fqn(self):
        if self.parent is not None and self.parent.name == 'Pin':
            return self.name + ' = ' + self.parent.fqn

        if self.__kwargs:
            if 'params' in self.__kwargs or 'value' in self.__kwargs:
                if self.parent.fqn is None:                     # allows to pass only one value, so you can declare a variable. e.g.: [fw_config]                            
                    global_variable_names.append(self.name)     # prevents to import the variable
                    return self.name                            # if value is a string, it needs double quotes. e.g.: value = "touch.firmware_config"
                
                return self.parent.fqn + '.' + self.name

            return self.name + ' = ' + self.parent.fqn

        if self.name == 'RGBDisplay':
            return 'rgb_display.RGBDisplay'

        if self.name == 'SDLDisplay':
            return 'sdl_display.SDLDisplay'

        if self.name == 'SDLPointer':
            return 'sdl_pointer.SDLPointer'

        if self.name == 'I2C':
            return 'i2c.I2C'

        if self.name == 'Spi3Wire':
            return 'spi3wire.Spi3Wire'

        if self.name == 'SPI':
            return 'machine.SPI'

        if self.name == 'SDCard':
            return 'machine.SDCard'

        if self.name.lower() in display_drivers:
            return self.name.lower() + '.' + self.name

        if self.name.lower() in indev_drivers:
            return self.name.lower() + '.' + self.name

        if self.name in io_expanders:
            return self.name

        if self.name in ('I80Bus', 'SPIBus', 'I2CBus', 'RGBBus'):
            return 'lcd_bus.' + self.name

        if self.parent is None:
            return None

        if self.parent.name:
            return self.parent.fqn + '.' + self.name

        return self.name

    @property
    def var_names(self):
        if self.__kwargs:
            fqn = self.fqn
            if '=' in fqn:

                return [fqn.split('=')[0].strip()]

            return []

        var_names = []

        for child in self.__children:
            if isinstance(child, (TOMLConditional, TOMLException)):
                continue
            var_names.extend(child.var_names) 

        return var_names

    @property
    def constants(self):
        res = []
        
        if not self.__children:
            for key, value in list(self.__kwargs.items()):
                if not isinstance(value, int) or key == 'value':
                    continue

                name = self.name.upper()

                key_upper = key.upper()
                if name not in key_upper:
                    key_upper = name + '_' + key_upper

                res.append(f'_{key_upper} = const({value})')
                self.__kwargs[key] = f'_{key_upper}'
        else:
            for child in self.__children:
                if isinstance(child, (TOMLConditional, TOMLException)):
                    continue

                res.extend(child.constants)
        
        return res

    def __str__(self):
        if self.parent is None:
            global_variable_names.extend(self.var_names)
            output = []
            output.extend(global_constants)
            output.extend(self.constants)
            output.insert(0,'')
            output.append('')
            for child in self.__children:
                if isinstance(child, (TOMLConditional, TOMLException)):
                    output.append('')
                elif child.name not in global_variable_names:
                    module = child.fqn.split('.')[0]
                    
                    if module not in self.imports and module not in used_imports:
                        self.imports.append(module)
                        used_imports.append(module)
                        output.insert(0,f'import {module}')
                output.append(str(child))
                
                if isinstance(child, (TOMLConditional)):
                    output.append(' ')
            for imp in global_imports:
                output.insert(0, f'import {imp}')
            
            if output:
                output = [
                    'from micropython import const',
                    'import lvgl as lv',
                    '',
                ] + output
            return '\n'.join(output)

        if self.__children and not self.__kwargs:
            output = [str(child) for child in self.__children]
            return '\n'.join(output)

        fqn = self.fqn
        
        if len(self.__kwargs) == 1:
            key = list(self.__kwargs.keys())[0]
            value = list(self.__kwargs.values())[0]
            if key == 'params':
                output = ''
                for param in self.__kwargs[key]:
                    if isinstance(param, str) and '.' in param:
                        mod = param.split('.', 1)[0]
                        if (
                            mod not in used_imports and
                            mod not in global_variable_names and (
                                mod in display_drivers or
                                mod in indev_drivers or
                                mod in io_expanders
                            )
                        ):
                            output.insert(0,f'import {mod}\n\n')
                            used_imports.append(mod)

                params = ', '.join(str(itm) for itm in self.__kwargs[key])
                output += f'{fqn}({params})'
                return output
            else:
                output = ''
                if (
                    isinstance(self.__kwargs[key], str) and
                    '.' in self.__kwargs[key]
                ):
                    mod = self.__kwargs[key].split('.', 1)[0]
                    if (
                        mod not in used_imports and
                        mod not in global_variable_names and (
                            mod in display_drivers or
                            mod in indev_drivers or
                            mod in io_expanders
                        )
                    ):
                        output.insert(0, f'import {mod}\n\n')
                        used_imports.append(mod)
                if key == 'value' and value is True:     # allows to call a function without arguements, without getting an import
                    output += f'{fqn}()'                 # ["var = func"]
                    return output                        # value = true --> "var = func()"               
                if key == 'value' and value is not True:
                    output += f'{fqn} = ' + str(self.__kwargs[key])
                else:
                    output += f'{fqn}({key}={str(self.__kwargs[key])})'
                
                return output
        else:
            output = []

            for v in self.__kwargs.values():
                if not (isinstance(v, str) and '.' in v):
                    continue

                mod = v.split('.', 1)[0]
                if (
                    mod not in used_imports and
                    mod not in global_variable_names and (
                        mod in display_drivers or
                        mod in indev_drivers or
                        mod in io_expanders
                    )
                ):
                    output.insert(0, f'import {mod}')
                    used_imports.append(mod)
            if output:
                output.append('')

            params = ',\n'.join(f'    {k}={str(v)}' for k, v in self.__kwargs.items() if not isinstance(v, dict))
            if params:
                output.append(f'{fqn}(\n{params}\n    )\n')
            else:
                raise RuntimeError

            for child in self.__children:
                output.append(self.name + '.' + str(child).split('.', 2)[-1])

            if len(output) > 2:
                output.append('')
                
            return '\n'.join(output)

#-----------------------------------------------------------------------------        
# TOMLException adds a new class. In the toml. file, the first element between   
# the[]brackets must contain 'exception', but can´ be set freely.All elements
# with the same name are contained to one block, like the TOMLConditional.
#
# The second element has to be one of the following arguements:
# -try, except, else, finally
# Some simple code expressions are implemented:
# -class (call an instance of a class)
# -func (function calls)
# -calc (calculating numbers) 
# 
# [exception.try] simply becomes --> 'try:', same for 'else' and 'finally'
# 
# [exception.except]
# type = "Exception"
# letter = "e"   --> 'except Exception as e:'
#
# [exception.raise}
# error = "Error message:"
# letter = "e"      --> 'print("Error message:",e)
#
# [exception.func]
# instance = "some_variable"
# function = "your_function"
# data = "something or empty"        --> 'some_variable = your_function(something)
#
# [exception.calc]
# instance = "some_variable"
# operator = "+-*/..."
# value1 = "something"
# value2 = "anything"       --> 'some_variable = something +-*/ anything'
#
# [exception.class]
# instance = "instance"
# class = "module.class"
# key1 = "value1"
# key2 = "value2"        --> 'instance = module.class(
#                                key = value,
#                                key2 = value2
#                                )                       
#----------------------------------------------------------------------------- 

class TOMLExceptionObject:
    
    def __init__(self, name, parent=None, **kwargs):
        global indt, actual
        self.name = name
        self.parent = parent
        self.__children = []
        
        for key, value in list(kwargs.items())[:]:
            if isinstance(value, dict): 
                self.__children.append(TOMLExceptionObject(key, self, **value))
                del kwargs[key]
        self.__kwargs = kwargs

    def check_imports(self, item):
        module = item.split('.',1)[0]
        if module not in used_imports:
            global_imports.append(module)
            used_imports.append(module)    
        return    
    
    def add_constants(self, _inst):
        res = []
        
        if not self.__children:
            for key, value in self.__kwargs.items():
                if not isinstance(value, int):
                    continue
                name = key.upper()
                _inst = _inst.split('.', 1)[0]
                inst = _inst.upper()
                line = (f'_{inst}_{name} = const({value})')
                if line not in used_constants:
                    global_constants.append(line)
                used_constants.append(line)
        else:        
            for child in self.__children:
                res.append(self.add_constants)
        
        return res
    
    def get_exception(self):
        __data = []
        match self.name:
            case 'try' | 'else' | 'finally': 
                return f'{self.name}:'
            case 'except':
                return f'except {self.__kwargs['type']} as {self.__kwargs['letter']}:' 
            case 'raise':
                return f'    print("{self.__kwargs['error']}", {self.__kwargs['letter']}\n'      
            case 'func':
                for key,value in self.__kwargs.items():
                    match key:
                        case 'instance': __inst = value
                        case 'function': __func = value
                        case _: __data.append(f'{value})')
                __data.insert(0,f'    {__inst} = {__func}(')        
                code = ''.join(__data)
                return code               
            case 'class':
                for key,value in self.__kwargs.items():
                    match key:
                        case 'instance': __inst = value
                        case 'class': __cls = value
                        case _: __data.append(f'        {key} = {value},')  
                __data.insert(0, f'    {__inst} = {__cls}(')
                __data.append(f'        )')                
                code = '\n'.join(__data)
                glob_const = self.add_constants(__inst)
                self.check_imports(__cls)
                return code                
            case 'calc':
                for key,value in self.__kwargs.items():
                    match key:
                        case 'instance': __inst = value
                        case 'operator': __oper = value
                        case 'value1': __val1 = value 
                        case 'value2': __val2 = value
                        case _: raise RuntimeError('Unsupported key in toml. file detected!')    
                __data.append(f'    {__inst} = {__val1} {__oper} {__val2}')        
                code = ''.join(__data)
                return code                
            case _:
                raise RuntimeError('Unable to locate exception argument')     

    def is_exception(self):
        excp = self.get_exception()        
        return excp is not None        

        
    def get_objects(self):
        res = []

        base_exception = self.parent
        while not isinstance(base_exception, TOMLException):
            base_exception = base_exception.parent

        if self.is_exception():
            for child in self.__children:
                res.extend(child.get_objects())
               
        else:
            if 'value' in self.__kwargs:
                names = []
                parent = self.parent
                
                while parent.name and not isinstance(parent, TOMLException):
                    names.insert(0, parent.name)
                    parent = parent.parent

                while names and not base_exception.has_variable_name('.'.join(names)):
                    names.pop(0)

                names.append(self.name)
                var_name = '.'.join(names)
                base_excepiton.add_variable_name(var_name)
                res.append(f'{var_name} = {self.__kwargs["value"]}')

            elif 'params' in self.__kwargs:
                params = ', '.join(str(item) for item in self.__kwargs['params'])
                if self.name == 'del':
                    res.append(f'{self.name} {params}')
                else:
                    res.append(f'{self.name}({params})')
                return res
                
            for child in self.__children:
                lines = child.get_objects()
                for line in lines:
                    if ' = ' in line:
                        var_name = line.split(' = ', 1)[0]
                        if base_exception.has_variable_name(var_name):
                            res.append(line)
                            continue
                    else:
                        try:
                            func_name = line.split('(', 1)[0]
                            if base_exception.has_variable_name(func_name):
                                res.append(line)
                                continue

                            func_name = func_name.split('.', 1)[0]
                            if base_exception.has_variable_name(func_name):
                                res.append(line)
                                continue
                        except IndexError:
                            pass

                    if line.startswith('del '):
                        res.append(line)
                    else:
                        res.append(f'{self.name}.{line}')                
        return res

    def is_variable(self):
        return 'value' in self.__kwargs

    def is_function(self):
        return 'params' in self.__kwargs
         

class TOMLException:    
    
    def __init__(self, name, parent=None, **kwargs):
        
        self.name = name
        self.parent = parent
        self.__kwargs = kwargs
        self.__children = []


        for key, value in list(self.__kwargs.items())[:]:
            if isinstance(value, dict):
                self.__children.append(TOMLExceptionObject(key, self, **value))
                del kwargs[key]
            elif isinstance(value, list):
                value = value.pop(0)
                self.__children.append(TOMLExceptionObject(key, self, **value))

        self.__kwargs = kwargs
        
        code = []
        for child in self.__children:
            excp = child.get_exception()
            if excp is not None and child.is_exception():                 
                code.append(excp)                
                continue

            else:
                raise RuntimeError('Unable to locate exception argument')

        for child in self.__children:
            code.extend([f'    {line}' for line in child.get_objects()])  #--> 3.10
        self.__code = '\n'.join(code)
        
    def add_variable_name(self, name):
        if name not in self.__variable_names:
            self.__variable_names.append(name)

    def has_variable_name(self, name):
        return name in self.__variable_names    
        
    def __str__(self):
        return self.__code


class TOMLConditionalObject:

    def __init__(self, name, parent=None, **kwargs):
        self.name = name
        self.parent = parent
        self.__children = []
        for key, value in list(kwargs.items())[:]:
            if isinstance(value, dict):
                self.__children.append(TOMLConditionalObject(key, self, **value))
                del kwargs[key]
        self.__kwargs = kwargs

    def get_conditional(self):
        if 'not_equal' in self.__kwargs:
            return f'{self.name} != {self.__kwargs["not_equal"]}'
        elif 'equal' in self.__kwargs:
            return f'{self.name} == {self.__kwargs["equal"]}'
        elif 'greater_than' in self.__kwargs:
            return f'{self.name} > {self.__kwargs["greater_than"]}'
        elif 'less_than' in self.__kwargs:
            return f'{self.name} < {self.__kwargs["less_than"]}'
        elif 'greater_than_or_equal' in self.__kwargs:
            return f'{self.name} >= {self.__kwargs["greater_than_or_equal"]}'
        elif 'less_than_or_equal' in self.__kwargs:
            return f'{self.name} <= {self.__kwargs["less_than_or_equal"]}'
        elif 'is' in self.__kwargs:
            return f'{self.name} is {self.__kwargs["is"]}'
        elif 'is_not' in self.__kwargs:
            return f'{self.name} is not {self.__kwargs["is_not"]}'
        elif 'in' in self.__kwargs:
            return f'{self.name} in {self.__kwargs["in"]}'
        elif 'not_in' in self.__kwargs:
            return f'{self.name} not in {self.__kwargs["not_in"]}'
        else:
            for child in self.__children:
                res = child.get_conditional()
                if res is not None:
                    return f'{self.name}.{res}'

    def is_conditional(self):
        cond = self.get_conditional()
        return cond is not None and not cond.startswith(f'{self.name}.')

    def get_objects(self):
        res = []
        base_conditional = self.parent

        while not isinstance(base_conditional, TOMLConditional):
            base_conditional = base_conditional.parent

        if self.is_conditional():
            for child in self.__children:                
                res.extend(child.get_objects())               
        else:
            if 'value' in self.__kwargs:
                names = []
                parent = self.parent
                while parent.name and not isinstance(parent, TOMLConditional):
                    names.insert(0, parent.name)
                    parent = parent.parent

                while names and not base_conditional.has_variable_name('.'.join(names)):
                    names.pop(0)

                names.append(self.name)
                var_name = '.'.join(names)
                base_conditional.add_variable_name(var_name)
                res.append(f'{var_name} = {self.__kwargs["value"]}')

            elif 'params' in self.__kwargs:
                params = ', '.join(str(item) for item in self.__kwargs['params'])
                if self.name == 'del':
                    res.append(f'{self.name} {params}')
                else:
                    res.append(f'{self.name}({params})')

                return res

            for child in self.__children:
                lines = child.get_objects()
                for line in lines:
                    if ' = ' in line:
                        var_name = line.split(' = ', 1)[0]
                        if base_conditional.has_variable_name(var_name):
                            res.append(line)
                            continue
                    else:
                        try:
                            func_name = line.split('(', 1)[0]
                            if base_conditional.has_variable_name(func_name):
                                res.append(line)
                                continue

                            func_name = func_name.split('.', 1)[0]
                            if base_conditional.has_variable_name(func_name):
                                res.append(line)
                                continue
                        except IndexError:
                            pass

                    if line.startswith('del '):
                        res.append(line)
                    else:
                        res.append(f'{self.name}.{line}')
        return res

    def is_variable(self):
        return 'value' in self.__kwargs

    def is_function(self):
        return 'params' in self.__kwargs


class TOMLConditional:

    def __init__(self, name, parent=None, **kwargs):
        self.name = name
        self.parent = parent
        self.__children = []
        self.__variable_names = []

        for key, value in list(kwargs.items())[:]:
            if isinstance(value, dict):
                self.__children.append(TOMLConditionalObject(key, self, **value))
                del kwargs[key]

        self.__kwargs = kwargs

        code = []
        for child in self.__children:
            cond = child.get_conditional()

            if cond is not None:
                code.append(f'if {cond}:')
                break
            else:
                raise RuntimeError('Unable to locate conditional argument')

        for child in self.__children:
            code.extend([f'    {line}' for line in child.get_objects()])  #--> 4.10
        self.__code = '\n'.join(code)

    def add_variable_name(self, name):
        if name not in self.__variable_names:
            self.__variable_names.append(name)

    def has_variable_name(self, name):
        return name in self.__variable_names

    def __str__(self):        
        return self.__code


class TOMLmcu:

    def __init__(self, mcu):
        name = mcu.mcu
        build_args = mcu.build_args

        command = [name]
        for arg, value in build_args.items():
            if arg.islower():
                build_arg = '--' + arg.replace('_', '-')
                if isinstance(value, bool) and not value:
                    raise SyntaxError(
                        'optionless build commands must be set to "true"\n'
                        f'if they are used in the toml file. ({arg} = {repr(value)})'
                    )
            else:
                build_arg = arg

            if not isinstance(value, bool):
                build_arg = f'{build_arg}={value}'

            command.append(build_arg)

        self.build_command = command


base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

display_driver_path = os.path.join(base_path, 'api_drivers/common_api_drivers/display')
indev_driver_path = os.path.join(base_path, 'api_drivers/common_api_drivers/indev')
io_expander_path = os.path.join(base_path, 'api_drivers/common_api_drivers/io_expander')


display_drivers = [file for file in os.listdir(display_driver_path) if not file.endswith('.wip') and not file.endswith('.py')]
indev_drivers = [file for file in os.listdir(indev_driver_path) if file.endswith('.py')]    # returns the filenames without cropping
io_expanders = [file for file in os.listdir(io_expander_path) if file.endswith('.py')]


def run(toml_path, output_file):

    if not os.path.exists(toml_path):
        raise RuntimeError(f'inable to locate .toml ({toml_path})')

    try:
        with open(toml_path, 'r') as f:
            toml_data = toml.load(f)
        toml_obj = TOMLObject('', **toml_data)
        t_data = str(toml_obj)

        if t_data:
            with open(output_file, 'w') as f:
                f.write(t_data)

        displays = [f'DISPLAY={item}' for item in toml_obj.imports if item in display_drivers]
        indevs = [f'INDEV={item}' for item in toml_obj.imports if item + '.py' in indev_drivers]    # ".py" needs to be added to item to compare with filelist
        expanders = [f'EXPANDER={item}' for item in toml_obj.imports if item + '.py' in io_expanders]   # ".py" needs to be added to item to compare with filelist

        if toml_obj.mcu_obj is None:
            build_command = []
        else:
            build_command = toml_obj.mcu_obj.build_command

        for display in displays[:]:
            if display not in build_command:
                build_command.append(display)

        for indev in indevs[:]:
            if indev not in build_command:
                build_command.append(indev)

        for expander in expanders[:]:
            if expander not in build_command:
                build_command.append(expander)
        print('Generated build command:\n',build_command)
        time.sleep(5)
        print('Generated Display.py:\n', t_data)
        
        return build_command

    except OSError as err:
        raise RuntimeError(f'Unable to write data to {output_file}') from err
    except Exception as err:  # NOQA
        raise SyntaxError(f'Unable to parse .toml file ({toml_path})') from err


