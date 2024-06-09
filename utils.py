import inspect


def getFormattedActions():
    formated_string = "\n"
    for action in Action.actions:
        formated_string += f"[{action}] ({Action.actions[action]['parameters']})\n{Action.actions[action]['description']}"
    return formated_string


class Action:
    actions = {}

    @classmethod
    def register(cls, func):
        """
        Decorator to register an action function.
        """
        action_name = func.__name__.upper()

        # Extract the first line of the docstring as the description
        if func.__doc__:
            doc_lines = func.__doc__.strip().split('\n')
            description = doc_lines[0]
            param_descriptions = {
                line.split(":")[0].strip(): line.split(":")[1].strip()
                for line in doc_lines[1:]
                if ":" in line
            }
        else:
            description = "No description provided"
            param_descriptions = {}

        # Use inspect to get the parameter names
        sig = inspect.signature(func)
        params = [param.name for param in sig.parameters.values()]

        # Combine the parameters with custom descriptions
        param_strs = [
            f"{param}: {param_descriptions[param]}" if param in param_descriptions else param
            for param in params
        ]
        param_str = ", ".join(param_strs)

        cls.actions[action_name] = {
            "description": description,
            "parameters": param_str
        }
        return func
