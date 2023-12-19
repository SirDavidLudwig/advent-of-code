from collections import defaultdict, Sequence
from itertools import combinations, combinations_with_replacement, count, permutations
import heapq
# import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from pqdict import pqdict
import regex as re
import sys
from typing import Optional, Tuple, Union

# Decorators ---------------------------------------------------------------------------------------

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

def debug(maxdepth=None):
	def decorator(f):
		stack = []
		depth = 0
		is_recursive = False
		def decorated(*args, __debug=True, **kwargs):
			nonlocal depth, is_recursive
			depth += 1
			result = f(*args, **kwargs)
			depth -= 1
			if maxdepth is None or depth < maxdepth:
				stack.append([
					f"Depth:             {depth + 1}",
					f"Arguments:         {args}",
					f"Keyword Arguments: {kwargs}",
					f"Output:            {result}",
				])
			if depth == 0:
				if __debug:
					for frame in stack[::-1]:
						if len(stack) == 1 and not is_recursive:
							frame = frame[1:]
						for row in frame:
							print(row)
						print()
				stack.clear()
			elif depth == 1:
				is_recursive = True
			return result
		return decorated
	return decorator

# Reading ------------------------------------------------------------------------------------------

def rlines(string: str):
    return string.split('\n')

def rgroups(string: str, delim='\n\n'):
    return string.split(delim)

def ints(values):
    if isinstance(values, str):
        values = re.findall(r"-?\d+", values)
    return list(map(int, values))

def npints(values):
    return np.array(ints(values))

def rmap(seq, func):
    """
    Recursive map
    """
    for item in seq:
        if isinstance(item, Sequence):
            yield type(item)(rmap(item, func))
        else:
            yield func(item)

# Numpy Short-hands --------------------------------------------------------------------------------

def arr(x):
    return np.array(x)

# Directionality -----------------------------------------------------------------------------------

@static_vars(delta_map={'n': (-1, 0), 's': (1, 0), 'w': (0, -1), 'e': (0, 1)})
def dirdelta(dir):
    if not isinstance(dir, str):
        return list(map(dirdelta, dir))
    return (0, 0) + np.sum([dirdelta.delta_map[c] for c in dir], axis=0)

def dirs(cards=True, diags=False, exclude=(), start='e', direction="counterclockwise", deltas=False):
    assert cards or diags
    assert direction in ("counterclockwise", "clockwise")
    if isinstance(exclude, str):
        exclude = (exclude,)
    step = 90 if cards^diags else 45
    sign = -1 if direction == "clockwise" else 1
    if (not cards and len(start) == 1) or (not diags and len(start) == 2):
        start = turn(start, 45) # align to axis
    result = list(filter(lambda x: x not in exclude, (
        turn(start, sign*angle) for angle in range(0, 360, step)
    )))
    if deltas:
        return zip(result, dirdelta(result))
    return result

@static_vars(arrow_map={'nw':'↖', 'ne': '↗', 'se': '↘', 'sw': '↙', 'w': '←', 'e': '→', 'n': '↑', 's': '↓'})
def dirarrow(dir):
    if not isinstance(dir, str):
        return list(map(dirarrow, dir))
    return dirarrow.arrow_map[dir]

@static_vars(rev_map={'n': 's', 's': 'n', 'w': 'e', 'e': 'w'})
def revdir(dir):
    if not isinstance(dir, str):
        return list(map(revdir, dir))
    return ''.join(revdir.rev_map[c] for c in dir)

@static_vars(dirs=("e", "ne", "n", "nw", "w", "sw", "s", "se"))
def turn(dir, amount):
    if not isinstance(dir, str):
        return [turn(d, amount) for d in dirs]
    steps = amount // 45
    return turn.dirs[(turn.dirs.index(dir) + steps) % len(turn.dirs)]

# Path Finding -------------------------------------------------------------------------------------

def astar(initial_state, neighbors, h = lambda *_: 0, init_cost=0):
    """
    Generic A* implementation.
    If a heuristic is not provided, the algorithm is equivalent to Dijkstra's
    """
    q = pqdict(
        {initial_state: (init_cost, h(initial_state), ())},
        key=lambda x: x[0]+x[1]
    )
    visited = set()
    while len(q) > 0:
        state, (cost, _, parents) = q.popitem()
        yield (cost, state, parents)
        visited.add(state)
        parents = parents + (state,)
        for ncost, neighbor in neighbors(state):
            if neighbor in visited:
                continue
            ncost = ncost + cost
            if neighbor in q and q[neighbor][0] < ncost:
                continue
            q[neighbor] = (ncost, h(neighbor), parents)

# Voxels -------------------------------------------------------------------------------------------

class Voxel:
    @classmethod
    def point(cls, loc: Union[int, tuple[int, ...]]):
        if isinstance(loc, int):
            loc = (loc,)
        return cls(loc, tuple(i+1 for i in loc))

    def __init__(self, start: Union[int, tuple[int, ...]], end: Union[int, tuple[int, ...]]):
        if isinstance(start, int):
            start = (start,)
        if isinstance(end, int):
            end = (end,)
        assert len(start) == len(end), "Start and end must contain the same number of elements"
        assert not any(x1 == x2 for x1, x2 in zip(start, end))
        self.start, self.end = zip(*map(sorted, zip(start, end)))

    def intersection(self, other: "Voxel") -> "Voxel":
        result = []
        for (a1, a2), (b1, b2) in zip(zip(self.start, self.end), zip(other.start, other.end)):
            if a1 >= b2 or a2 <= b1:
                # non-intersection
                return None
            result.append((max(a1, b1), min(a2, b2)))
        return Voxel(*zip(*result))

    def difference(self, other: "Voxel") -> list["Voxel"]:
        remaining_voxels = []
        voxel = self
        for axis, ((a1, a2), (b1, b2)) in enumerate(zip(zip(self.start, self.end), zip(other.start, other.end))):
            if a1 >= b2 or a2 <= b1:
                # non-intersection
                return [self]
            if b1 > a1:
                remaining, voxel = voxel.subdivide(b1, axis)
                remaining_voxels.append(remaining)
            if b2 < a2:
                voxel, remaining = voxel.subdivide(b2, axis)
                remaining_voxels.append(remaining)
        return remaining_voxels

    def subdivide(self, point: int, axis: int) -> Union[tuple["Voxel"], tuple["Voxel", "Voxel"]]:
        if not (self.start[axis] < point < self.end[axis]):
            return [self]
        a_end = list(self.end)
        b_start = list(self.start)
        a_end[axis] = b_start[axis] = point
        return [Voxel(self.start, tuple(a_end)), Voxel(tuple(b_start), self.end)]

    # def plot(self, **kwargs):
    #     assert len(self.start) == 2
    #     plt.fill(
    #         [self.start[0], self.end[0], self.end[0], self.start[0]],
    #         [self.start[1], self.start[1], self.end[1], self.end[1]],
    #         **kwargs)

    def offset(self, translation: Union[int, tuple[int, ...]]):
        if isinstance(translation, int):
            translation = (translation,)
        start = tuple(a+b for a, b in zip(self.start, translation))
        end = tuple(a+b for a, b in zip(self.end, translation))
        return Voxel(start, end)

    def volume(self) -> int:
        return int(np.product([b-a for a, b in zip(self.start, self.end)]))

    def __bool__(self):
        return all(a != b for a, b in zip(self.start, self.end))

    def __and__(self, other: "Voxel"):
        return self.intersection(other)

    def __sub__(self, other: "Voxel"):
        return self.difference(other)

    def __eq__(self, other: "Voxel"):
        return self.start == other.start and self.end == other.end

    def __repr__(self):
        return f"Voxel(start={self.start}, end={self.end})"


class VoxelMap:
    def __init__(self):
        self.voxel_map = []

    def items(self):
        return iter(self.voxel_map)

    def __getitem__(self, voxel: Union[int, tuple[int], Voxel]):
        if not isinstance(voxel, Voxel):
            voxel = Voxel.point(voxel)
        result = []
        for (key, value) in self.voxel_map:
            intersection = voxel & key
            if intersection is None:
                continue
            result.append((intersection, value))
        return result

    def __setitem__(self, voxel: Voxel, value):
        remaining_voxels = []
        indices_to_remove = []
        for i, (k, v) in enumerate(self.voxel_map):
            remaining = k - voxel
            if len(remaining) == 1 and remaining[0] == k:
                # Non-intersecting
                continue
            indices_to_remove.append(i)
            remaining_voxels.append((remaining, v))
        for i in reversed(indices_to_remove):
            del self.voxel_map[i]
        self.voxel_map.append((voxel, value))
        for (keys, v) in remaining_voxels:
            for key in keys:
                self.voxel_map.append((key, v))
