"""
Self-Modifying Code Examples in Python
WARNING: Use these techniques carefully - they can be dangerous!
"""
import inspect
import types
import sys
from io import StringIO

# ============================================
# METHOD 1: Dynamic Function Creation
# ============================================
class SelfModifyingAI:
    """AI that can create and modify its own methods"""

    def __init__(self):
        self.knowledge_base = {}
        self.custom_functions = {}

    def learn_function(self, name, code):
        """Learn a new function by compiling code"""
        try:
            # Create a new function from string
            exec(f"def {name}(self, *args, **kwargs):\n    " +
                 code.replace("\n", "\n    "), globals())

            # Bind it to this instance
            new_method = types.MethodType(globals()[name], self)
            setattr(self, name, new_method)
            self.custom_functions[name] = code

            return f"Learned new function: {name}"
        except Exception as e:
            return f"Error learning function: {e}"

    def modify_function(self, name, new_code):
        """Modify an existing function"""
        if hasattr(self, name):
            return self.learn_function(name, new_code)
        return f"Function {name} doesn't exist"

    def list_custom_functions(self):
        """List all custom functions"""
        return list(self.custom_functions.keys())

    def get_function_code(self, name):
        """Get the source code of a custom function"""
        if name in self.custom_functions:
            return self.custom_functions[name]
        return None


# ============================================
# METHOD 2: Code Generation and Execution
# ============================================
class CodeGenerator:
    """Generates and executes code dynamically"""

    @staticmethod
    def generate_class(class_name, methods):
        """Generate a complete class at runtime"""
        class_code = f"class {class_name}:\n"

        for method_name, method_body in methods.items():
            class_code += f"    def {method_name}(self):\n"
            class_code += f"        {method_body}\n\n"

        # Execute the code to create the class
        exec(class_code, globals())
        return globals()[class_name]

    @staticmethod
    def generate_function(func_name, parameters, body):
        """Generate a function at runtime"""
        func_code = f"def {func_name}({', '.join(parameters)}):\n"
        func_code += f"    {body}\n"

        exec(func_code, globals())
        return globals()[func_name]


# ============================================
# METHOD 3: Self-Modifying Code File
# ============================================
class SelfModifyingFile:
    """Modifies its own source code file"""

    def __init__(self, filename):
        self.filename = filename

    def read_own_code(self):
        """Read the current source code"""
        try:
            with open(self.filename, 'r') as f:
                return f.read()
        except Exception:
            return None

    def add_function_to_file(self, function_code):
        """Add a new function to the source file"""
        current_code = self.read_own_code()
        if current_code:
            # Add the new function before the last line
            lines = current_code.split('\n')
            # Insert before if __name__ == "__main__" if it exists
            insert_pos = -1
            for i, line in enumerate(lines):
                if 'if __name__' in line:
                    insert_pos = i
                    break

            if insert_pos > 0:
                lines.insert(insert_pos, '\n' + function_code + '\n')
            else:
                lines.append('\n' + function_code + '\n')

            # Write back to file
            with open(self.filename, 'w') as f:
                f.write('\n'.join(lines))

            return True
        return False

    def modify_function_in_file(self, old_func_name, new_code):
        """Replace a function in the source file"""
        current_code = self.read_own_code()
        if current_code:
            import re
            pattern = rf'def {old_func_name}\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
            new_code_block = f'def {old_func_name}' + new_code
            modified = re.sub(pattern, new_code_block, current_code, flags=re.DOTALL)

            with open(self.filename, 'w') as f:
                f.write(modified)

            return True
        return False


# ============================================
# METHOD 4: Runtime Class Modification
# ============================================
class EvolvingAgent:
    """Agent that evolves by adding capabilities"""

    def __init__(self):
        self.capabilities = []

    def add_capability(self, name, function):
        """Add a new capability (method) to this class"""
        setattr(self.__class__, name, function)
        self.capabilities.append(name)
        return f"Added capability: {name}"

    def remove_capability(self, name):
        """Remove a capability"""
        if hasattr(self.__class__, name):
            delattr(self.__class__, name)
            self.capabilities.remove(name)
            return f"Removed capability: {name}"
        return f"Capability {name} not found"

    def list_capabilities(self):
        """List all capabilities"""
        return self.capabilities


# ============================================
# METHOD 5: Meta-Class Programming
# ============================================
class SelfModifyingMeta(type):
    """Metaclass that allows classes to modify themselves"""

    def __new__(mcs, name, bases, dct):
        def add_method(cls, method_name, method_func):
            setattr(cls, method_name, method_func)

        dct['add_method'] = classmethod(add_method)
        return super().__new__(mcs, name, bases, dct)


class AdaptiveClass(metaclass=SelfModifyingMeta):
    """A class that can modify itself using the metaclass"""

    def __init__(self):
        self.data = {}


# ============================================
# METHOD 6: Dynamic Code Compilation
# ============================================
class DynamicCompiler:
    """Compiles and executes code dynamically"""

    @staticmethod
    def compile_and_run(code_string):
        """Compile and execute code from string"""
        try:
            compiled = compile(code_string, '<string>', 'exec')
            namespace = {}
            exec(compiled, namespace)
            return namespace
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def safe_eval(expression, allowed_names=None):
        """Safely evaluate expressions"""
        if allowed_names is None:
            allowed_names = {"__builtins__": {}}

        try:
            return eval(expression, allowed_names)
        except Exception as e:
            return f"Error: {e}"


# ============================================
# DEMONSTRATION
# ============================================
def demonstrate_self_modification():
    """Demonstrate various self-modification techniques"""

    print("=" * 60)
    print("SELF-MODIFYING CODE DEMONSTRATION")
    print("=" * 60)

    # Demo 1: Self-modifying AI
    print("\n1. SELF-MODIFYING AI")
    print("-" * 60)
    ai = SelfModifyingAI()

    result = ai.learn_function("greet", "return f'Hello, {args[0]}!'")
    print(result)
    print(f"Testing new function: {ai.greet('World')}")

    ai.learn_function("calculate", "return args[0] ** 2")
    print(f"Calculate 5^2: {ai.calculate(5)}")

    print(f"Custom functions: {ai.list_custom_functions()}")

    # Demo 2: Dynamic class generation
    print("\n2. DYNAMIC CLASS GENERATION")
    print("-" * 60)

    methods = {
        "speak": "return 'I can speak!'",
        "think": "return 'I can think!'"
    }

    DynamicRobot = CodeGenerator.generate_class("DynamicRobot", methods)
    robot = DynamicRobot()
    print(f"Robot speaks: {robot.speak()}")
    print(f"Robot thinks: {robot.think()}")

    # Demo 3: Dynamic function generation
    print("\n3. DYNAMIC FUNCTION GENERATION")
    print("-" * 60)

    add_func = CodeGenerator.generate_function(
        "dynamic_add",
        ["a", "b"],
        "return a + b"
    )
    print(f"Dynamic add(3, 7): {add_func(3, 7)}")

    # Demo 4: Evolving agent
    print("\n4. EVOLVING AGENT")
    print("-" * 60)

    agent = EvolvingAgent()

    def fly(self):
        return "I'm flying!"

    def swim(self):
        return "I'm swimming!"

    agent.add_capability("fly", fly)
    agent.add_capability("swim", swim)

    print(f"Capabilities: {agent.list_capabilities()}")
    print(agent.fly())
    print(agent.swim())

    # Demo 5: Adaptive class with metaclass
    print("\n5. ADAPTIVE CLASS WITH METACLASS")
    print("-" * 60)

    adaptive = AdaptiveClass()

    def new_method(self):
        return "This method was added at runtime!"

    AdaptiveClass.add_method("runtime_method", new_method)
    print(adaptive.runtime_method())

    # Demo 6: Dynamic compilation
    print("\n6. DYNAMIC CODE COMPILATION")
    print("-" * 60)

    code = """
def factorial(n):
    return 1 if n <= 1 else n * factorial(n-1)
result = factorial(5)
"""

    namespace = DynamicCompiler.compile_and_run(code)
    print(f"Factorial(5) from compiled code: {namespace.get('result')}")

    result = DynamicCompiler.safe_eval("2 ** 10")
    print(f"Safe eval of '2 ** 10': {result}")

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


# ============================================
# PRACTICAL SELF-IMPROVING AI EXAMPLE
# ============================================
class SelfImprovingAI:
    """AI that learns new skills and improves itself"""

    def __init__(self):
        self.skills = {}
        self.performance_log = []

        # Initialize with basic skills
        self.add_skill("analyze_sentiment", self._basic_sentiment)

    def _basic_sentiment(self, text):
        """Basic sentiment analysis"""
        positive = sum(1 for word in ["good", "great", "love"] if word in text.lower())
        negative = sum(1 for word in ["bad", "hate", "terrible"] if word in text.lower())
        return "positive" if positive > negative else "negative"

    def add_skill(self, name, function):
        """Add a new skill"""
        self.skills[name] = function
        setattr(self, name, types.MethodType(function, self))

    def improve_skill(self, name, improved_function):
        """Improve an existing skill"""
        if name in self.skills:
            self.add_skill(name, improved_function)
            return f"Improved skill: {name}"
        return f"Skill {name} doesn't exist"

    def learn_from_code(self, skill_name, code_string):
        """Learn a new skill from code string"""
        try:
            namespace = {}
            exec(f"def skill(self, *args, **kwargs):\n    " +
                 code_string.replace("\n", "\n    "), namespace)

            self.add_skill(skill_name, namespace['skill'])
            return f"Learned new skill: {skill_name}"
        except Exception as e:
            return f"Error: {e}"

    def list_skills(self):
        """List all available skills"""
        return list(self.skills.keys())


# Example usage
if __name__ == "__main__":
    demonstrate_self_modification()

    print("\n\n" + "=" * 60)
    print("SELF-IMPROVING AI EXAMPLE")
    print("=" * 60)

    ai = SelfImprovingAI()

    # Learn a new skill
    code = """
data = args[0]
return sum(data) / len(data)
"""
    print(ai.learn_from_code("calculate_average", code))

    # Use the new skill
    print(f"Average of [1,2,3,4,5]: {ai.calculate_average([1,2,3,4,5])}")

    # Learn another skill
    code2 = """
text = args[0]
return len(text.split())
"""
    print(ai.learn_from_code("count_words", code2))
    print(f"Words in 'Hello world how are you': {ai.count_words('Hello world how are you')}")

    print(f"\nAll skills: {ai.list_skills()}")
