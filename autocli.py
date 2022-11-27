import sys

class Option(object):

    @staticmethod
    def valid_opt(opt):
        if not isinstance(opt, str):
            return False
        return opt.isalnum()

    @staticmethod
    def valid_typestr(typestr):
        return typestr in {"", "FILE", "STR", "INT", "FLOAT"}

    @staticmethod
    def valid_description(description):
        return isinstance(description, str)

    @staticmethod
    def valid_default(default, typestr):
        if default is None:
            return True
        elif typestr in {"FILE", "STR"}:
            return isinstance(default, str)
        elif typestr == "INT":
            return isinstance(default, int)
        elif typestr == "FLOAT":
            return isinstance(default, float)
        else:
            return False

    def __init__(self, opt, typestr, description, default):

        assert self.valid_opt(opt)
        assert self.valid_typestr(typestr)
        assert self.valid_description(description)
        assert self.valid_default(default, typestr)

        self.opt = opt
        self.typestr = typestr
        self.description = description
        self.default = default

    @classmethod
    def decode(cls, opt, **kwargs):

        if not "description" in kwargs:
            kwargs["description"] = ""

        kwargs["opt"] = opt

        if "default" in kwargs:
            default = kwargs["default"]
            if isinstance(default, int):
                kwargs["typestr"] = "INT"
            elif isinstance(default, float):
                kwargs["typestr"] = "FLOAT"
            elif isinstance(default, str):
                if not "typestr" in kwargs:
                    kwargs["typestr"] = "STR"
        elif not "typestr" in kwargs:
            kwargs["typestr"] = ""
            kwargs["default"] = None
        else:
            kwargs["default"] = None

        return cls(kwargs["opt"], kwargs["typestr"], kwargs["description"], kwargs["default"])

    def usage_tokens(self):
        return ["-{}".format(self.opt), self.typestr, self.description, "[{}]".format(str(self.default)) if not self.default is None else ""]

class AutoCLI(object):

    def __init__(self):
        self.arguments = []
        self.options = []

    def add_argument(self, varname, token):
        assert isinstance(varname, str) and isinstance(token, str)
        self.arguments.append((varname, token))

    def add_option(self, varname, opt, **kwargs):
        self.options.append((varname, Option.decode(opt, **kwargs)))

    def generate_c_code(self):

        for header in ["stdio", "stdlib", "string", "unistd"]:
            yield "#include <{}.h>\n".format(header)

        yield "\n"
        yield "char progname[64];\n\n"
        yield "int usage()\n{\n"
        yield "    fprintf(stderr, \"%s [options] {}\\n\\n\", progname);\n".format(" ".join(a[1] for a in self.arguments))
        yield "    fprintf(stderr, \"Options:\\n\");\n"

        for option in self.options:
            optchar, optstr, optdesc, optdef = option[1].usage_tokens()
            line = "{} {} {}{} {}".format(optchar, optstr, " " * (5-len(optstr)), optdesc, optdef).rstrip()
            yield "    fprintf(stderr, \"    {}\\n\");\n".format(line)

        yield "    return -1;\n}\n\n"

        yield "int main(int argc, char *argv[])\n{\n    strncpy(progname, argv[0], 64);\n\n"
        yield "    if (argc < {}) return usage();\n\n".format(1+len(self.arguments))

        boolints = []
        option_defs = [[], ["c"], []]
        option_klist = {"STR": 0, "FILE": 0, "": 1, "INT": 1, "FLOAT": 2}
        opttok = []

        for varname, option in self.options:

            which = option_klist[option.typestr]

            if option.default is None:
                if option.typestr not in {"FILE", "STR"}: option_defs[which].append(varname)
                else: option_defs[which].append("{} = NULL".format(varname))
                if option.typestr == "": boolints.append(varname)
            else:
                option_defs[which].append("{} = {}".format(varname, option.default))

            if option.typestr == "": opttok.append(option.opt)
            else: opttok.append("{}:".format(option.opt))

        opttok.append("h")

        if len(option_defs[0]) > 0: yield "    char " + ", ".join("*{}".format(dec) for dec in option_defs[0]) + ";\n"
        if len(option_defs[1]) > 0: yield "    int " + ", ".join(dec for dec in option_defs[1]) + ";\n"
        if len(option_defs[2]) > 0: yield "    double " + ", ".join(dec for dec in option_defs[2]) + ";\n"

        yield "\n"

        if len(boolints) > 0: yield "    " + " = ".join(dec for dec in boolints) + " = 0;\n\n"

        yield "    while ((c = getopt(argc, argv, \"{}\")) >= 0)\n".format("".join(opttok))
        yield "    {\n"
        yield "        if (c == 'h') return usage();\n"

        for varname, option in self.options:
            if option.typestr in {"STR","FILE"}: dec = "optarg"
            elif option.typestr == "INT": dec = "atoi(optarg)"
            elif option.typestr == "FLOAT": dec = "atof(optarg)"
            elif option.typestr == "": dec = "1"
            yield "        else if (c == '{}') {} = {};\n".format(option.opt, varname, dec)

        yield "    }\n\n"

        yield "    if (optind + {} > argc)\n".format(len(self.arguments))
        yield "    {\n        return usage();\n    }\n\n"
        yield "    return 0;\n"

        yield "}\n"

    def generate_python_code(self):

        for header in ["sys", "getopt"]:
            yield "import {}\n".format(header)

        yield "\n"
        yield "def usage():\n"
        yield "    sys.stderr.write(\"Usage: python {{}} [options] {}\\n\\n\".format(sys.argv[0]))\n".format(" ".join(a[1] for a in self.arguments))
        yield "    sys.stderr.write(\"Options:\\n\")\n"

        for option in self.options:
            optchar, optstr, optdesc, optdef = option[1].usage_tokens()
            line = "{} {} {}{} {}".format(optchar, optstr, " " * (5-len(optstr)), optdesc, optdef).rstrip()
            yield "    sys.stderr.write(\"    {}\\n\")\n".format(line)

        yield "    return -1\n\n"

        yield "def main(argc, argv):\n\n"
        yield "    if argc < {}: return usage()\n\n".format(1+len(self.arguments))

        boolints = []
        option_defs = [[], [], []]
        option_klist = {"": 0, "STR": 0, "FILE": 0, "": 1, "INT": 1, "FLOAT": 2}
        opttok = []

        for varname, option in self.options:

            which = option_klist[option.typestr]

            if option.default is None:
                if option.typestr == "": option_defs[which].append("{} = False".format(varname))
                else: option_defs[which].append("{} = None".format(varname))
            else:
                option_defs[which].append("{} = {}".format(varname, option.default))

            if option.typestr == "": opttok.append(option.opt)
            else: opttok.append("{}:".format(option.opt))

        opttok.append("h")

        for i in range(len(option_defs)):
            for dec in option_defs[i]:
                yield "    {}\n".format(dec)
            yield "\n"

        yield "    try: opts, args = getopt.gnu_getopt(argv[1:], \"{}\")\n".format("".join(opttok))
        yield "    except getopt.GetoptError as err:\n"
        yield "        sys.stderr.write(\"error: {}\\n\".format(err))\n"
        yield "        return usage()\n\n"

        yield "    for o, a in opts:\n"
        yield "        if o == \"-h\": return usage()\n"

        for varname, option in self.options:
            if option.typestr in {"FILE", "STR"}:
                yield "        elif o == \"-{}\": {} = a\n".format(option.opt, varname)
            elif option.typestr == "INT":
                yield "        elif o == \"-{}\": {} = int(a)\n".format(option.opt, varname)
            elif option.typestr == "FLOAT":
                yield "        elif o == \"-{}\": {} = float(a)\n".format(option.opt, varname)
            else:
                yield "        elif o == \"-{}\": {} = True\n".format(option.opt, varname)

        yield "\n"

        yield "    if len(args) != {}:\n".format(len(self.arguments))
        yield "        return usage()\n\n"

        yield "if __name__ == \"__main__\":\n    sys.exit(main(len(sys.argv), sys.argv))\n"

autocli = AutoCLI()
autocli.add_argument("input_fname", "<in.fa>")
autocli.add_option("readmap_fname", "D", description="dump read name map", typestr="FILE")
autocli.add_option("line_width", "l", description="number of residues per line; 0 for entire sequence", default=80)
autocli.add_option("comments", "n", description="include original read name as comment")
autocli.add_option("zero_indexing", "0", description="use zero-based indexing")
autocli.add_option("test2", "Z", default=3.1415, description="yAh")

for line in autocli.generate_python_code():
    sys.stdout.write(line)


