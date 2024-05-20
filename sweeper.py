import random
from enum import Enum
from typing import Union, Optional


DEBUG_BOARD = False  # enable a constant, non-randomized debug board


class GameState(Enum):
	idle = "idle"
	playing = "playing"
	won = "won"
	lost = "lost"


class CellState(Enum):
	flagged = "flagged"
	questioned = "questioned"


class Game:
	def __init__(
			self,
			size: tuple[int, int],
			mine_count: int,
			seed: Optional[Union[int, float, str, bytes, bytearray]] = None
	):
		self.seed = seed
		self.random = random.Random(seed)
		self.size: tuple[int, int] = size
		self.mine_count = mine_count
		self.state: GameState = GameState.idle

		self.mine_points = set()
		self.questioned_points = set()
		self.flagged_points = set()
		self.last_click: Optional[tuple[int, int]] = None

		self._cell_opened_grid: list[list[bool]] = [
			([False] * self.size[0]) for _ in range(self.size[1])
		]

	def is_won(self):
		if self.state == GameState.won:
			return True

		if self.state == GameState.lost:
			return False

		non_mine_points = set([
			(x, y) for x in range(self.size[0]) for y in range(self.size[1])
		]) - self.mine_points

		for point in non_mine_points:
			# every non-mine point must be opened
			if not self.is_opened(point):
				return False

		self.state = GameState.won
		return True

	def _flag_all_mines(self):
		for point in self.mine_points:
			self.flag(point)

	def generate_board(self, disallowed_points: list[tuple[int, int]] = None):
		possible_points = list(
			(x, y) for x in range(self.size[0]) for y in range(self.size[1]) if (disallowed_points is None) or ((x, y) not in disallowed_points)
		)
		self.mine_points = set()

		for _ in range(self.mine_count):
			point_index = self.random.randint(0, len(possible_points) - 1)
			point = possible_points[point_index]
			possible_points.pop(point_index)
			self.mine_points.add(point)

		assert (len(possible_points) + len(self.mine_points)) == (self.size[0] * self.size[1]) - (len(disallowed_points) if disallowed_points else 0)
		del possible_points

		if DEBUG_BOARD:
			self.mine_points = {
				(0, 3),
				(2, 3),
				(6, 4),
				(6, 4),
				(8, 4),
				(6, 6),
				(3, 5),
				(4, 5),
				(2, 6),
				(3, 7),
				(2, 8)
			}
		self.state = GameState.playing
		self.last_click = None

	def is_flagged(self, point: tuple[int, int]) -> bool:
		return point in self.flagged_points

	def get_flagged_points(self) -> list[tuple[int, int]]:
		return list(self.flagged_points)

	def flag(self, point: tuple[int, int]):
		if self.is_opened(point):
			print(f"warn: tried to flag opened point {point}")
			return

		self.flagged_points.add(point)
		self.questioned_points.discard(point)  # cant be flagged and questioned .. almost seems like i should use a different data structure huh.

	def unflag(self, point: tuple[int, int]):
		self.questioned_points.discard(point)
		self.flagged_points.discard(point)

	def question(self, point: tuple[int, int]):
		self.questioned_points.add(point)
		self.flagged_points.discard(point)

	def unquestion(self, point: tuple[int, int]):
		self.questioned_points.discard(point)
		self.flagged_points.discard(point)

	def is_questioned(self, point: tuple[int, int]) -> bool:
		return point in self.questioned_points

	def is_mine(self, point: tuple[int, int]) -> bool:
		return point in self.mine_points

	def is_opened(self, point: tuple[int, int]) -> bool:
		return self._cell_opened_grid[point[0]][point[1]]

	def _set_opened(self, point: tuple[int, int]):
		self._cell_opened_grid[point[0]][point[1]] = True

	def in_range(self, point: tuple[int, int]) -> bool:
		return (0 <= point[0] < self.size[0]) and (0 <= point[1] < self.size[1])

	def proximity_count(self, point: tuple[int, int]) -> int:
		if self.is_mine(point):
			return -1

		return sum(
			(self.is_mine((x, y)) if self.in_range((x, y)) else False)
			for x in range(point[0]-1, point[0]+2)
			for y in range(point[1]-1, point[1]+2)
		)

	def open(self, point: tuple[int, int]):
		if self.state != GameState.playing:
			raise ValueError("can't open cell, not playing!!")

		self.last_click = point

		if self.is_opened(point):
			print(f"warn: tried to click opened cell {point}")
			return

		if self.is_flagged(point):
			print(f"warn: tried to click flagged cell {point}")
			return

		start_point = point

		# if self.state != GameState.playing:
		# 	raise ValueError("not playing rn")

		if self.is_mine(start_point):
			print("clicked a mine, losing!!")

			self.state = GameState.lost
			# for mine_point in self.mine_points:
			# 	self._set_cell(mine_point, CellState.open)
			return

		# im learning what a flood fill is
		# https://en.wikipedia.org/wiki/Flood_fill#Stack-based_recursive_implementation_(four-way)
		# this is actually an 8 way algorithm bc i reach all corners and adjacents.
		stack = []
		stack.append(start_point)
		while len(stack) > 0:
			point = stack.pop(0)
			# print(f"Visiting {point}")

			if self.is_opened(point):
				continue

			inside = (not self.is_mine(point)) and (not self.is_flagged(point))
			if inside:
				# print(f"{n_point} IN")
				self._set_opened(point)

			if inside and self.proximity_count(point) == 0:
				new_points = []
				for x_off in (-1, 0, 1):
					for y_off in (-1, 0, 1):
						if x_off == 0 and y_off == 0:
							continue
						new_points.append((point[0] + x_off, point[1] + y_off))

				# west = (point[0] - 1, point[1])
				# east = (point[0] + 1, point[1])
				# north = (point[0], point[1] - 1)
				# south = (point[0], point[1] + 1)

				for new_point in new_points:
					if self.in_range(new_point):
						stack.append(new_point)

			if self.is_won():
				self._flag_all_mines()


def test():
	game = Game(size=(9, 9), mine_count=6, seed=0)
	game.generate_board(disallowed_points=[(5, 4)])

	def render_game():
		print("   ", end="")
		for x in range(game.size[0]):
			print(f"{x:<2}", end="")
		print("\n", end="")

		for y in range(game.size[1]):
			print(f"{y:>2}", end=" ")
			for x in range(game.size[0]):
				cell_state = game.get_cell_state((x, y))
				if cell_state == CellState.open:
					char = "  "
				else:
					char = "░░"

				print(char, end="")
			print("\n",  end="")

	while True:
		render_game()

		point = None
		while not point:
			pnt_input = input("> ")
			try:
				comma_idx = pnt_input.find(",")
				if comma_idx <= 0:
					continue
				x = int(pnt_input[:comma_idx], 10)
				y = int(pnt_input[comma_idx+1:], 10)
				if not game.in_range((x, y)):
					continue
				point = (x, y)
			except (IndexError, ValueError):
				continue
		game.open(point)

	"""
	print(game.is_mine((0, 5)))
	for y in range(game.size[1]):
		for x in range(game.size[0]):
			count = game.proximity_count((x, y))
			print((
				" " if count == 0 else
				"X" if count == -1 else count
			), end=" ")

		print("\n", end="")
	"""


if __name__ == '__main__':
	test()
