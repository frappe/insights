import sqlglot.expressions as sge

_drop_init = sge.Drop.__init__


def _drop_init_from_this(self, **args):
    # sqlglot 30.18 moved Drop's target from `this` to `tables`. ibis 11 still passes `this`,
    # which renders `DROP TABLE IF EXISTS` with no name. Delete once ibis ships ibis#12104.
    if "this" in args:
        args["tables"] = [args.pop("this")]
    _drop_init(self, **args)


sge.Drop.__init__ = _drop_init_from_this
