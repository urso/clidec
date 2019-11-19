import argparse


class _namespaced:
    """
    All objects implementing _namespaced can be used as namespaces
    for adding sub commands.
    """

    def __init__(self):
        self._subcommands = {}

    def namespace(self, name, *opts):
        """ Create new sub-namespace without runnable function.

        If users execute the namespace by name the help text will be printed.
        """

        ns = Namespace(name, *opts)
        self.add_subcommand(ns)

    def add_subcommand(self, sub):
        """ Add a single sub-command or namespace to the current namespace.
        """

        self._subcommands[sub.name] = sub

    def add_subcommands(self, *cmds):
        """ Add a list of sub-commands and namespaces to the current namespace.
        """
        for cmd in cmds:
            self.add_subcommand(cmd)

    def command(self, *opts):
        """ Create sub-command decorator.

        command creates a new sub-command decorator that can can be used to add
        a function as sub-command to the current namespace.
        """
        return self._make_command(Command, *opts)

    def rawcommand(self, *opts):
        """ Create raw sub-command capturing arguments.

        Creates a RawCommand, that will collect all arguments into
        a string array, without interpreting any arguments.

        The raw command is added to the current namespace. All arguments
        before the command name will be removed from the input array.

        Raw commands can be used to define aliases for other external scripts,
        as arguments are captured as is.
        """
        return self._make_command(RawCommand, *opts)

    def _make_command(self, cmdclass, *opts):
        def do(fn):
            cmd = cmdclass(fn.__name__, fn, *opts)
            for opt in opts:
                opt.init_cmd(cmd)
            self.add_subcommand(cmd)
            return cmd

        if len(opts) == 1 and callable(opts[0]):
            fn, opts = opts[0], []
            return do(fn)
        return do

    def _add_subparsers(self, parser):
        if len(self._subcommands) == 0:
            return

        subparsers = _SubcommandList(parser.prog)
        for cmd in self._subcommands.values():
            cmd._add_subparser(subparsers)

        parser.add_argument("command",
                            action=_Subaction,
                            actions=subparsers.commands,
                            choices=list(subparsers.commands.keys()),
                            option_strings=[],
                            nargs=argparse.PARSER,
                            )


class Namespace(_namespaced):
    """ Namespace defines a namespace that can hold sub-commands and other
    namespace.

    When an user executes the 'namespace' a help-string with the available
    sub-commands will be printed.

    A namespace is callable. When called it will parse the arguments and call
    the selected sub-command.
    """

    def __init__(self, name, *opts):
        super(Namespace, self).__init__()
        self.name = name
        self.doc = name
        self._opts = opts
        for opt in self._opts:
            opt.init_namespace(self)

    def __call__(self, *args, **kwargs):
        self.run(*args, **kwargs)

    def run(self, parser=None, args=None):
        if not parser:
            parser = argparse.ArgumentParser()
        self._init_argparse(parser)
        args = parser.parse_args(args)
        args.func(args)

    def _add_subparser(self, action):
        parser = action.add_parser(self.name, description=self.doc)
        self._init_argparse(parser)

    def _init_argparse(self, parser):
        def fn(args):
            parser.print_help()
            exit(1)
        for opt in self._opts:
            opt.init_args(parser)
        parser.set_defaults(func=fn)
        self._add_subparsers(parser)


class Command(_namespaced):
    """ Executable sub-command. """

    def __init__(self, name, fn, *opts):
        super(Command, self).__init__()
        self.name = name
        self.fn = fn
        self._opts = opts
        self.doc = ""

    def __call__(self, *args, **kwargs):
        self.fn(*args, **kwargs)

    def _add_subparser(self, action):
        doc = self.doc if self.doc else self.fn.__doc__
        parser = action.add_parser(self.name, description=doc)
        self._init_argparse(parser)

    def _init_argparse(self, parser):
        for opt in self._opts:
            opt.init_args(parser)
        parser.set_defaults(func=self.fn)
        self._add_subparsers(parser)


class RawCommand:
    """ Executable raw sub-command """

    def __init__(self, name, fn, *args, **kwargs):
        self.name = name
        self.fn = fn
        self.doc = ""

    def _add_subparser(self, action):
        parser = action.add_rawparser(self.name, self.fn, description=self.doc)
        parser.set_defaults(func=self.fn)

    def add_subcommand(self, cmd):
        raise Exception("Can not add subcommands to raw commands")


class _SubcommandList:
    def __init__(self, prog):
        self.commands = {}
        self.prog_prefix = prog

    def add_parser(self, name, *args, **kwargs):
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self.prog_prefix, name)

        parser = argparse.ArgumentParser(*args, **kwargs)
        self.commands[name] = parser
        return parser

    def add_rawparser(self, name, fn, *args, **kwargs):
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self.prog_prefix, name)

        parser = _RawParser("raw", *args, **kwargs)
        self.commands[name] = parser
        return parser


class _RawParser:
    def __init__(self, dest, *args, **kwargs):
        self.dest = dest
        self._defaults = {}

    def parse_args(self, args, namespace=None):
        if namespace is None:
            namespace = argparse.Namespace()
        for k, v in self._defaults.items():
            setattr(namespace, k, v)
        setattr(namespace, self.dest, args)
        return namespace

    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)


class _Subaction(argparse.Action):
    def __init__(self, actions, *args, **kwargs):
        super(_Subaction, self).__init__(*args, **kwargs)
        self.actions = actions

    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return

        name = values[0]
        args = values[1:]
        setattr(namespace, self.dest, name)

        try:
            parser = self.actions[name]
        except:
            choices = ", ".join(self.actions.keys())
            raise argparse.ArgumentError(self,
                                         f"unknown parser {name}, ({choices})")

        # parse all the remaining options into the namespace
        subnamespace = parser.parse_args(args)
        for k, v in vars(subnamespace).items():
            setattr(namespace, k, v)


class cmdopt:
    """ Commando and namespace optionals.

    classes implementing cmdopt can modify namespaces, commandos and 
    the argparse parser.
    """

    def init_namespace(self, namespace): pass

    def init_cmd(self, cmd): pass

    def init_args(self, parser): pass


class command_name(cmdopt):
    """ Overwrite the command or namespace name.  """

    def __init__(self, name):
        self._name = name

    def init_namespace(self, ns):
        ns.name = self._name

    def init_cmd(self, cmd):
        cmd.name = self._name


class argument(cmdopt):
    """ Add an argument to a namespace or command.  

    The argument options supports all the same options as are
    supported by ArgumentParser.add_argument.
    """

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def init_args(self, parser):
        parser.add_argument(*self._args, **self._kwargs)


class with_commands(cmdopt):
    """ Add a list of existing commands and namespace to the new namespace.
    """

    def __init__(self, *commands):
        self._commands = commands

    def init_namespace(self, ns): self._add_commands(ns)

    def init_cmd(self, cmd): self._add_commands(cmd)

    def _add_commands(self, cmd):
        for sub in self._commands:
            cmd.add_subcommand(sub)


def root(*opts):
    """ Create standalone anonymous root namespace.

    Existing namespaces can be included via with_commands. The root namespace
    acts as the entrypoint when running your application. It should be used to
    define the main function like:

        main = root(
            with_commands(
               ...,
            )
        )

        if __name__ == "__main__":
            main()
    """

    return Namespace("", *opts)


def namespace(name, *opts):
    """ Namespace declares a new standalone namespace.

    Standalone namespaces can be added to other namespaces via with_commands or
    executed directly.
    """

    ns = Namespace(name, *opts)
    return ns
