# advent-of-code

My environment, tools, and solutions to Advent of Code.

## Installation

Start by installing `aoctools` using the following:

```bash
pip3 install -e ./aoctools
```

## Puzzle Initialization

Initialize a puzzle using the `aoc` script. This will download your puzzle input and open it in a `less` instance, as well as set up a templated `part1.py` and empty `part2.py` and automatically opening them in VS code.

```bash
# e.g.: ./aoc 2023 1
./aoc <year> <day>
```

## Live Running/Debugging

In VSCode, the "Live Puzzle Input" and "Live Sample Input" debug task will automatically run your scripts as you make changes providing the appropriate puzzle input. The included `.vscode/settings.json` enables auto-saving with a 250ms delay from typing.
