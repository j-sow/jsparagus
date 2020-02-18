from .ordered import OrderedFrozenSet
from .grammar import InitNt

class Action:
    __slots__ = [
        "read",    # Set of trait names which are consumed by this action.
        "write",   # Set of trait names which are mutated by this action.
        "_hash",   # Cached hash.
    ]

    def __init__(self, read, write):
        assert isinstance(read, list)
        assert isinstance(write, list)
        self.read = read
        self.write = write
        self._hash = None

    def is_condition(self):
        "Unordered condition, which accept or not to reach the next state."
        return False
    def condition(self):
        "Return the conditional action."
        raise TypeError("Action::condition_flag not implemented")
    def update_stack(self):
        """Change the parser stack, and resume at a different location. If this function
        is defined, then the function reduce_with should be implemented."""
        return False
    def reduce_with(self):
        "Returns the non-terminal with which this action is reducing with."
        assert self.update_stack()
        raise TypeError("Action::reduce_to not implemented.")
    def shifted_action(self, shifted_terms):
        "Returns the same action shifted by a given amount."
        return self

    def maybe_add(self, other):
        """Implement the fact of concatenating actions into a new action which can have
        a single state instead of multiple states which are following each others."""
        actions = []
        if isinstance(self, Seq):
            actions.extend(list(self.actions))
        else:
            actions.append(self)
        if isinstance(other, Seq):
            actions.extend(list(other.actions))
        else:
            actions.append(other)
        if any([a.is_condition() for a in actions]):
            return None
        if any([a.update_stack() for a in actions[:-1]]):
            return None
        return Seq(actions)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        if sorted(self.read) != sorted(other.read):
            return False
        if sorted(self.write) != sorted(other.write):
            return False
        for s in self.__slots__:
            if getattr(self, s) != getattr(other, s):
                return False
        return True

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        def hashed_content():
            yield self.__class__
            yield "rd"
            for alias in self.read:
                yield alias
            yield "wd"
            for alias in self.write:
                yield alias
            for s in self.__slots__:
                yield repr(getattr(self, s))
        self._hash = hash(tuple(hashed_content()))
        return self._hash

    def __lt__(self, other):
        return hash(self) < hash(other)

    def __repr__(self):
        return str(self)

class Reduce(Action):
    """Define a reduce operation which pops N elements of he stack and pushes one
    non-terminal. The replay attribute of a reduce action corresponds to the
    number of stack elements which would have to be popped and pushed again
    using the parser table after reducing this operation. """
    __slots__ = 'nt', 'replay', 'pop'
    def __init__(self, nt, pop, replay = 0):
        name = nt.name
        if isinstance(name, InitNt):
            name = "Start_" + name.goal.name
        super().__init__([], ["nt_" + name])
        self.nt = nt    # Non-terminal which is reduced
        self.pop = pop  # Number of stack elements which should be replayed.
        self.replay = replay # List of terms to shift back
    def __str__(self):
        return "Reduce({}, {}, {})".format(self.nt, self.pop, self.replay)
    def update_stack(self):
        return True
    def reduce_with(self):
        return self
    def shifted_action(self, shifted_terms):
        return Reduce(self.nt, self.pop, replay = self.replay + len(shifted_terms))

class Lookahead(Action):
    """Define a Lookahead assertion which is meant to either accept or reject
    sequences of terminal/non-terminals sequences."""
    __slots__ = 'sequences', 'accept'
    def __init__(self, sequences, accept):
        assert isinstance(sequences, OrderedFrozenSet)
        assert isinstance(accept, bool)
        super().__init__([], [])
        self.sequences = sequences
        self.accept = accept
    def is_condition(self):
        return True
    def condition(self):
        return self
    def __str__(self):
        return "Lookahead({}, {})".format(self.sequences, self.accept)
    def shifted_action(self, shifted_terms):
        shift = len(shifted_terms)
        new_seqs = []
        match = False
        for seq in self.sequences:
            if shifted_terms[:len(seq)] == seq[:shift]:
                if seq[shift:] == []:
                    return self.accept
                new_seqs.append(seq[shift:])
        if new_seqs == []:
            return not self.accept
        return Lookahead(new_seqs, accept)

class FilterFlag(Action):
    """Define a filter which check for one value of the flag, and continue to the
    next state if the top of the flag stack matches the expected value."""
    __slots__ = 'flag', 'value'
    def __init__(self, flag, value):
        super().__init__(["flag_" + flag], [])
        self.flag = flag,
        self.value = value
    def is_condition(self):
        return True
    def condition(self):
        return self
    def __str__(self):
        return "FilterFlag({}, {})".format(self.flag, self.value)

class PushFlag(Action):
    """Define an action which pushes a value on a stack dedicated to the flag. This
    other stack correspond to another parse stack which live next to the
    default state machine and is popped by PopFlag, as-if this was another
    reduce action. This is particularly useful to raise the parse table from a
    LR(0) to an LR(k) without needing as much state duplications."""
    __slots__ = 'flag', 'value'
    def __init__(self, flag, value):
        super().__init__([], ["flag_" + flag])
        self.flag = flag,
        self.value = value
    def __str__(self):
        return "PushFlag({}, {})".format(self.flag, self.value)

class PopFlag(Action):
    """Define an action which pops a flag from the flag bit stack."""
    __slots__ = 'flag',
    def __init__(self, flag):
        super().__init__(["flag_" + flag], ["flag_" + flag])
        self.flag = flag
    def __str__(self):
        return "PopFlag({})".format(self.flag)

class FunCall(Action):
    """Define a call method operation which reads N elements of he stack and
    pushpathne non-terminal. The replay attribute of a reduce action correspond
    to the number of stack elements which would have to be popped and pushed
    again using the parser table after reducing this operation. """
    __slots__ = 'method', 'offset', 'args', 'set_to'
    def __init__(self, method, alias_read, alias_write, args, set_to = None, offset = 0):
        super().__init__(alias_read, alias_write)
        self.method = method     # Method and argument to be read for calling it.
        self.offset = offset     # Offset to add to each argument offset.
        self.args = args         # Tuple of arguments offsets.
        self.set_to = set_to     # Temporary variable name to set with the result.
    def __str__(self):
        return "FunCall({}, {}, {}, {})".format(self.method, self.offset, self.args, self.set_to)
    def shifted_action(self, shifted_terms):
        shift = len(shifted_terms)
        return FunCall(self.method, self.read, self.write, self.args, self.set_to, offset = self.offset + shift)

class Seq(Action):
    """Aggregate multiple actions in one statement. Note, that the aggregated
    actions should not contain any condition or action which are mutating the
    state. Only the last action aggregated can update the parser stack"""
    __slots__ = 'actions',
    def __init__(self, actions):
        assert isinstance(actions, list)
        read = [ rd for a in actions for rd in a.read ]
        write = [ wr for a in actions for wr in a.write ]
        super().__init__(read, write)
        self.actions = tuple(actions)   # Ordered list of actions to execute.
        assert all([not a.is_condition() for a in actions[1:]])
        assert all([not a.update_stack() for a in actions[:-1]])
    def __str__(self):
        return "Seq({})".format(repr(self.actions))
    def is_condition(self):
        return self.actions[0].is_condition()
    def condition(self):
        return self.actions[0]
    def update_stack(self):
        return self.actions[-1].update_stack()
    def reduce_with(self):
        return self.actions[-1].reduce_with()
    def shifted_action(self, shift = 1):
        actions = list(map(lambda a: a.shifted_action(shift), self.actions))
        return Seq(actions)
