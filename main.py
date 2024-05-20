import json
import math
import colorsys
from pathlib import Path
from typing import Optional, Callable
from enum import Enum

import wx
import wx.lib.buttons
import wx.lib.inspection

from sweeper import Game, CellState, GameState

THEME = "winmine"

THEMES_PATH = Path(__file__).parent / "themes"
ASSETS_PATH = THEMES_PATH / THEME


class SmileFace(Enum):
	COOL = "cool"
	SAD = "sad"
	SURPRISED = "surprised"
	HAPPY = "happy"


COLOR_HIGHLIGHT: wx.Colour
COLOR_NEUTRAL: wx.Colour
COLOR_SHADOW: wx.Colour


def make_bitmaps(source: wx.Image, size: tuple[int, int], count: int) -> list[wx.Bitmap]:
	bitmaps = []
	for index in range(count):
		rect = wx.Rect(
			x=0,
			y=index * size[1],
			width=size[0],
			height=size[1]
		)
		image: wx.Image = source.GetSubImage(rect)
		if not image:
			raise ValueError(f"{index=} out of bounds!!")
		bitmaps.append(image.ConvertToBitmap())
	return bitmaps


def draw_border(
	dc: wx.DC,
	width: int,
	top_left: wx.Position,
	bottom_right: wx.Position,

	top: wx.Colour,
	bottom: wx.Colour,
	left: wx.Colour,
	right: wx.Colour,

	inset: bool = False
):
	pen_top = wx.Pen(top)
	pen_bottom = wx.Pen(bottom)
	pen_left = wx.Pen(left)
	pen_right = wx.Pen(right)

	root_top_left = top_left
	root_bottom_right = bottom_right - (1, 1)

	if inset:
		root_top_left += (width, width)
		root_bottom_right -= (width, width)

	lines = []
	pens = []

	for offset in range(1, width + 1):
		top_left = root_top_left - (offset, offset)
		bottom_right = root_bottom_right + (offset, offset)

		top_right = wx.Position(bottom_right[0], top_left[1])
		bottom_left = wx.Position(top_left[0], bottom_right[1])

		lines.extend((
			(top_left[0], top_left[1], top_right[0], top_right[1]),  # top
			(top_right[0], top_right[1], bottom_right[0], bottom_right[1]),  # right
			(bottom_right[0], bottom_right[1], bottom_left[0], bottom_left[1]),  # bottom
			(bottom_left[0], bottom_left[1], top_left[0], top_left[1])  # left
		))

		pens.extend((
			pen_top,
			pen_right,
			pen_bottom,
			pen_left
		))

	dc.DrawLineList(
		lines=lines,
		pens=pens
	)


class LCD(wx.Panel):
	def __init__(
		self,
		parent: wx.Window,
		value: int = 0,
		digits: int = 3,
		pad_zeros: bool = True
	):
		super().__init__(parent=parent)

		self._value = value
		self.digits = digits
		self.pad_zeros = pad_zeros

		self._bitmap_size = (13, 23)
		self._bitmaps = make_bitmaps(
			source=wx.Image(str(ASSETS_PATH / "420.bmp")),
			size=self._bitmap_size,
			count=12
		)

		self.SetMinSize((
			self._bitmap_size[0] * self.digits,
			self._bitmap_size[1]
		))

		self._char_bitmaps = self._get_bitmaps()

		self.Bind(wx.EVT_PAINT, self._on_paint)

	def _on_paint(self, _):
		dc = wx.PaintDC(self)
		for (index, bitmap) in enumerate(self._char_bitmaps):
			dc.DrawBitmap(
				bmp=bitmap,
				pt=(
					self._bitmap_size[0] * index,
					0
				)
			)

	def set_value(self, value: int):
		self._value = value
		self._char_bitmaps = self._get_bitmaps()
		self.Refresh()

	def _get_bitmaps(self):
		(
			bmp_minus,
			bmp_space,
			*bmp_digits
		) = self._bitmaps

		bmp_digits.reverse()

		value = self._value
		value = min(value, pow(10, self.digits) - 1)
		value = max(value, -(pow(10, self.digits - 1) - 1))

		if self.pad_zeros:
			format_string = "{:0" + str(self.digits) + "}"
		else:
			format_string = "{:" + str(self.digits) + "}"

		str_value = format_string.format(value)
		if len(str_value) != self.digits:
			raise ValueError("failed to digit format")

		return [
			bmp_minus if char == "-" else
			bmp_space if char == " " else
			bmp_digits[int(char)]
			for char in str_value
		]


class Scoreboard(wx.Panel):
	def __init__(
		self,
		parent: wx.Window,
		on_smile_click: Callable[[], None]
	):
		super().__init__(parent=parent)

		self.sizer = wx.BoxSizer(wx.HORIZONTAL)

		self._smile_bitmaps = make_bitmaps(
			source=wx.Image(str(ASSETS_PATH / "430.bmp")),
			size=(24, 24),
			count=5
		)

		self._flags_lcd = LCD(
			parent=self,
			value=0,
			digits=3
		)
		self.sizer.Add(self._flags_lcd, flag=wx.ALL, border=6)

		self.sizer.AddStretchSpacer()

		self._smile_button = wx.lib.buttons.GenBitmapButton(
			parent=self,
			size=(24, 24),
			bitmap=self._smile_bitmaps[4],
			style=wx.BORDER_NONE
		)
		self._smile_button.Bind(wx.EVT_BUTTON, lambda _: on_smile_click())
		self._smile_button.labelDelta = 0
		self._smile_button.SetBitmapSelected(self._smile_bitmaps[0])
		self.sizer.Add(self._smile_button, flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP, border=1)

		self.sizer.AddStretchSpacer()

		self._time_lcd = LCD(
			parent=self,
			value=0,
			digits=3
		)
		self.sizer.Add(self._time_lcd, flag=wx.ALL, border=6)

		self.SetSizer(self.sizer)

		self.Bind(wx.EVT_PAINT, self._on_paint)

	def set_smile_face(self, face: SmileFace):
		self._smile_button.SetBitmapLabel(self._smile_bitmaps[
			1 if face == SmileFace.COOL else
			2 if face == SmileFace.SAD else
			3 if face == SmileFace.SURPRISED else
			4 if face == SmileFace.HAPPY else
			0
		])
		self._smile_button.Refresh()

	def _on_paint(self, _):
		dc = wx.PaintDC(self)

		draw_border(
			dc=dc, width=1,

			top_left=self._flags_lcd.GetPosition(),
			bottom_right=self._flags_lcd.GetPosition() + self._flags_lcd.GetSize(),

			top=COLOR_SHADOW, left=COLOR_SHADOW,
			right=COLOR_HIGHLIGHT, bottom=COLOR_HIGHLIGHT
		)

		draw_border(
			dc=dc, width=1,

			top_left=self._smile_button.GetPosition(),
			bottom_right=self._smile_button.GetPosition() + self._smile_button.GetSize(),

			top=COLOR_SHADOW, left=COLOR_SHADOW, right=COLOR_SHADOW, bottom=COLOR_SHADOW
		)

		draw_border(
			dc=dc, width=1,

			top_left=self._time_lcd.GetPosition(),
			bottom_right=self._time_lcd.GetPosition() + self._time_lcd.GetSize(),

			top=COLOR_SHADOW, left=COLOR_SHADOW,
			right=COLOR_HIGHLIGHT, bottom=COLOR_HIGHLIGHT
		)

	def set_flags_value(self, value: int):
		self._flags_lcd.set_value(value)
		self._flags_lcd.Refresh()

	def set_time_value(self, value: int):
		self._time_lcd.set_value(value)
		self._time_lcd.Refresh()


class Minefield(wx.Panel):
	def __init__(
		self,
		parent: wx.Window,
		on_click: Callable[[tuple[int, int]], None],
		on_right_click: Callable[[tuple[int, int]], None]
	):
		super().__init__(
			parent=parent
		)

		self.cell_bitmaps = make_bitmaps(
			source=wx.Image(str(ASSETS_PATH / "410.bmp")),
			size=(16, 16),
			count=16
		)

		self.button_grid: list[list[wx.lib.buttons.GenBitmapButton]] = []
		self.sizer: Optional[wx.GridSizer] = None
		self.size: Optional[tuple[int, int]] = None

		self._last_game: Optional[Game] = None

		self._on_click = on_click
		self._on_right_click = on_right_click

	def initialize_board(self, size: tuple[int, int]):
		# if self.size == size:
		# 	print("ignoring init-board call because size is the same")
		# 	return

		self.size = size

		width, height = size

		if self.sizer:
			self.sizer.Clear(delete_windows=True)
			# self.sizer.Destroy()
			del self.sizer

		button_grid = []

		(
			bmp_unopened,
			bmp_flagged,
			bmp_questioned,
			bmp_mine_red,
			bmp_mine_x,
			bmp_mine,
			bmp_questioned_pressed,
			bmp_8,
			bmp_7,
			bmp_6,
			bmp_5,
			bmp_4,
			bmp_3,
			bmp_2,
			bmp_1,
			bmp_0
		) = self.cell_bitmaps

		sizer = wx.GridSizer(width, height, 0, 0)
		self.SetSizer(sizer, deleteOld=True)

		def make_button(point: tuple[int, int]):
			button = wx.lib.buttons.GenBitmapButton(
				parent=self,
				size=(16, 16),
				style=wx.BORDER_NONE,
				bitmap=bmp_unopened
			)
			button.SetMinSize((16, 16))
			button.Bind(wx.EVT_BUTTON, lambda _: self._on_click(point))
			button.Bind(wx.EVT_RIGHT_DOWN, lambda _: self._on_right_click(point))
			button.labelDelta = 0  # dont move when down
			button.SetBitmapSelected(bmp_0)
			return button

		for x in range(width):
			col = []
			for y in range(height):
				button = make_button((x, y))
				col.append(button)

			button_grid.append(col)

		for y in range(height):
			for x in range(width):
				sizer.Add(button_grid[x][y])

		self.button_grid = button_grid
		self.sizer = sizer
		print("DONE!!")
		self.Layout()
		self.Fit()
		self.Refresh()
		print("DONE AND FIT!!!")

	def update(self, game: Game):
		print(f"minefield update called w {game}")
		if not game:
			raise ValueError("no game!!!")

		if self._last_game != game:
			print("new game, re-initializing...")
			self._last_game = game
			self.initialize_board(game.size)

		# if game.state == GameState.idle:
		# 	return

		(
			bmp_unopened,
			bmp_flagged,
			bmp_questioned,
			bmp_mine_red,
			bmp_mine_x,
			bmp_mine,
			bmp_questioned_pressed,
			*number_bmps
		) = self.cell_bitmaps

		bmp_empty = number_bmps[-1]

		width = len(self.button_grid)
		height = len(self.button_grid[0])

		game_over = game.state == GameState.lost
		for x in range(width):
			for y in range(height):
				point = (x, y)
				button = self.button_grid[x][y]
				opened = game.is_opened(point)
				flagged = game.is_flagged(point)
				questioned = game.is_questioned(point)
				# print(f"Updated... {point=} {state=}")

				if opened:
					count = game.proximity_count(point)
					count_img = number_bmps[-count - 1]
					button.SetBitmapLabel(count_img)
					button.SetBitmapSelected(count_img)
				elif flagged:
					if game_over and not game.is_mine(point):
						# if game is over and this flag was WRONG, show the X mine logo
						button.SetBitmapLabel(bmp_mine_x)
						button.SetBitmapSelected(bmp_mine_x)
					else:
						button.SetBitmapLabel(bmp_flagged)
						button.SetBitmapSelected(bmp_flagged)
				elif questioned:
					button.SetBitmapLabel(bmp_questioned)
					button.SetBitmapSelected(bmp_questioned_pressed)
				elif game_over and game.is_mine(point):
					if game.last_click == point:
						button.SetBitmapLabel(bmp_mine_red)
						button.SetBitmapSelected(bmp_mine_red)
					else:
						button.SetBitmapLabel(bmp_mine)
						button.SetBitmapSelected(bmp_mine)
				else:
					button.SetBitmapLabel(bmp_unopened)
					if game_over:
						button.SetBitmapSelected(bmp_unopened)
					else:
						button.SetBitmapSelected(bmp_empty)

		self.Refresh()


class GameFrame(wx.Frame):
	def __init__(self):
		super().__init__(
			parent=None,
			title="sweeper",
			size=(512, 512),
			style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
		)

		self.SetBackgroundColour(COLOR_NEUTRAL)
		self.button_grid: list[list[wx.lib.buttons.GenBitmapButton]] = []

		self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer = wx.BoxSizer(wx.VERTICAL)

		self.scoreboard = Scoreboard(parent=self, on_smile_click=self.on_smile_click)
		self.sizer.Add(self.scoreboard, flag=wx.EXPAND | wx.BOTTOM, border=11)

		self.game_size = (9, 9)
		self.game_mines = 10

		self.minefield = Minefield(
			parent=self,
			on_click=self.on_click,
			on_right_click=self.on_right_click
		)
		self.minefield.initialize_board(self.game_size)
		self.sizer.Add(self.minefield)

		self.outer_sizer.Add(self.sizer, border=10, flag=wx.ALL)
		self.SetSizer(self.outer_sizer)

		self.game: Optional[Game] = None
		self.init_new_game()
		self.update()

		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.Fit()

		self.game_stopwatch = wx.StopWatch()
		self.game_timer = wx.Timer()
		self.game_timer.Bind(wx.EVT_TIMER, lambda _: self.update_timer())

	def update_timer(self):
		self.scoreboard.set_time_value(
			round(self.game_stopwatch.Time() / 1000) + 1
		)
		# adding 1 and not flooring because for some reason thats how the minesweeper one works
		# anmd cuz i gotta make sure i dont skip any.

	def update(self):
		self.minefield.update(self.game)

		if self.game.state in {GameState.won, GameState.lost}:
			# game is over
			self.stop_game()

		if self.game.state == GameState.won:
			self.scoreboard.set_smile_face(SmileFace.COOL)
		elif self.game.state == GameState.lost:
			self.scoreboard.set_smile_face(SmileFace.SAD)
		elif self.game.state in {GameState.playing, GameState.idle}:
			self.scoreboard.set_smile_face(SmileFace.HAPPY)

		self.scoreboard.set_flags_value(self.game.mine_count - len(self.game.flagged_points))

	def on_smile_click(self):
		print("smile clicked")
		if self.game.state != GameState.idle:
			print("Game started, making new game")
			self.stop_game()
			self.init_new_game()
			self.update()

	def on_paint(self, event: wx.PaintEvent):
		dc = wx.PaintDC(self)

		background_colour = self.GetBackgroundColour()

		draw_border(
			dc=dc,
			width=3,
			inset=True,

			top_left=wx.Position(0, 0),
			bottom_right=self.GetClientSize(),

			top=COLOR_HIGHLIGHT, left=COLOR_HIGHLIGHT,
			right=background_colour, bottom=background_colour
		)

		draw_border(
			dc=dc,
			width=2,
			top_left=self.scoreboard.GetPosition(),
			bottom_right=self.scoreboard.GetPosition() + self.scoreboard.GetSize(),

			top=COLOR_SHADOW, left=COLOR_SHADOW,
			right=COLOR_HIGHLIGHT, bottom=COLOR_HIGHLIGHT
		)

		draw_border(
			dc=dc,
			width=3,
			top_left=self.minefield.GetPosition(),
			bottom_right=self.minefield.GetPosition() + self.minefield.GetSize(),

			top=COLOR_SHADOW, left=COLOR_SHADOW,
			right=COLOR_HIGHLIGHT, bottom=COLOR_HIGHLIGHT
		)

	def init_new_game(self):
		self.game = Game(
			size=self.game_size,
			mine_count=self.game_mines
		)
		self.scoreboard.set_flags_value(self.game.mine_count)
		self.scoreboard.set_time_value(0)

	def start_game(self, point: tuple[int, int]):
		if self.game.state != GameState.idle:
			raise ValueError("can't start started game")

		self.game.generate_board(disallowed_points=[point])
		self.game_stopwatch.Start(milliseconds=0)  # this param means "Start time"
		self.game_timer.Start(milliseconds=1000)  # and this param means "interval". thx very not confusing.
		self.update_timer()

	def stop_game(self):
		self.game_timer.Stop()
		self.game_stopwatch.Pause()

	def on_click(self, point: tuple[int, int]):
		if self.game and self.game.state == GameState.idle:
			self.start_game(point)

		if self.game is None or self.game.state != GameState.playing:
			return

		if not (self.game.is_opened(point) or self.game.is_flagged(point)):
			# only click unopened, unflagged points
			self.game.open(point)
			self.update()

	def on_right_click(self, point: tuple[int, int]):
		if self.game is None or self.game.state in {GameState.won, GameState.lost}:
			return

		if self.game.is_flagged(point):
			self.game.question(point)
		elif self.game.is_questioned(point):
			self.game.unquestion(point)
		elif not self.game.is_opened(point):
			self.game.flag(point)

		self.update()


def main():
	global COLOR_HIGHLIGHT, COLOR_NEUTRAL, COLOR_SHADOW
	
	app = wx.App()
	# whatever. bad code.
	with open(ASSETS_PATH / "colors.json", "r") as file:
		colors_data = json.load(file)
		COLOR_HIGHLIGHT = wx.Colour(colors_data["highlight"])
		COLOR_NEUTRAL = wx.Colour(colors_data["neutral"])
		COLOR_SHADOW = wx.Colour(colors_data["shadow"])

	frame = GameFrame()
	frame.Show()
	# wx.lib.inspection.InspectionTool().Show()
	app.MainLoop()


if __name__ == "__main__":
	main()
