# -*- coding: utf-8 -*-
"""
NoteBook - a light notebook + drawing app for phones, built with Kivy.
Theme: yellow / white / black.
  - Notebook : plain text notes, saved as .txt
  - Drawing  : pen, shapes, eraser, text objects, images (move / resize), saved as .nbl
Single file: save as main.py, put your PNG icons in a folder named "icons" next to it.
"""
import base64
import io
import json
import math
import os
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, InstructionGroup, Line, PopMatrix,
                           PushMatrix, Rectangle, RoundedRectangle, Translate)
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup, get_color_from_hex, platform

# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------
YELLOW = get_color_from_hex('#FFC400')
BLACK = get_color_from_hex('#111111')
DARK = get_color_from_hex('#1E1E1E')
DARK2 = get_color_from_hex('#333333')
LIGHT = get_color_from_hex('#F3F3F3')
GREY = get_color_from_hex('#9A9A9A')
RED = get_color_from_hex('#C62828')
WHITE = (1, 1, 1, 1)
HANDLE = dp(24)

PALETTE = ['#111111', '#FFFFFF', '#FFC400', '#E53935', '#FB8C00', '#43A047',
           '#1E88E5', '#8E24AA', '#EC407A', '#6D4C41', '#9E9E9E', '#00ACC1']

# --------------------------------------------------------------------------
# ICON SETTINGS  (edit these numbers to tune every icon's size)
# --------------------------------------------------------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    BASE_DIR = os.getcwd()
ICON_DIR = os.path.join(BASE_DIR, 'icons')

# False = icons keep their ORIGINAL colors (as you designed them)
# True  = icons are tinted by the button text color (white icons only)
TINT_ICONS = False

# Button icons: fraction of the button's smaller side (0.3 small ... 0.9 big)
DEFAULT_ICON_SCALE = 0.60
ICON_SCALE = {
    # top bars
    'back': 0.60, 'save': 0.60, 'save_as': 0.60, 'new': 0.60, 'open': 0.60,
    'menu': 0.60, 'close': 0.55, 'undo': 0.60, 'redo': 0.60,
    # file dialog
    'folder': 0.60, 'folder_up': 0.60, 'export_png': 0.60,
    # drawing tools
    'pen': 0.66, 'line': 0.66, 'rect': 0.66, 'oval': 0.66, 'eraser': 0.66,
    'text': 0.66, 'image': 0.66, 'select': 0.66,
    # property bar
    'edit': 0.60, 'bold': 0.58, 'italic': 0.58, 'underline': 0.58,
    'font_smaller': 0.60, 'font_larger': 0.60, 'color': 0.62,
    'bring_front': 0.60, 'delete': 0.60, 'smaller': 0.60, 'larger': 0.60,
    # menu
    'background': 0.60, 'clear_page': 0.60,
    # recent files list
    'file_txt': 0.62, 'file_nbl': 0.62,
}

# Big icons: size in dp
ICON_DP = {'note_card': 56, 'draw_card': 56, 'app_icon': 72, 'folder': 26}

_icon_cache = {}


def icon_exists(name):
    return bool(name) and os.path.isfile(os.path.join(ICON_DIR, name + '.png'))


def icon_tex(name, px):
    """Load icons/<name>.png shrunk ONCE to the pixel size really needed
    (cached on disk in icons/_small). Returns None if missing."""
    px = max(32, int(math.ceil(px / 16.0)) * 16)
    key = (name, px)
    if key in _icon_cache:
        return _icon_cache[key]
    tex = None
    path = os.path.join(ICON_DIR, name + '.png')
    if os.path.isfile(path):
        small = os.path.join(ICON_DIR, '_small', '%s_%d.png' % (name, px))
        try:
            if os.path.isfile(small) and \
                    os.path.getmtime(small) >= os.path.getmtime(path):
                tex = CoreImage(small).texture
            else:
                try:
                    from PIL import Image as PILImage
                    im = PILImage.open(path).convert('RGBA')
                    im = im.resize((px, px), PILImage.LANCZOS)
                except ImportError:
                    im = None
                if im is None:
                    tex = CoreImage(path, mipmap=True).texture
                else:
                    try:
                        os.makedirs(os.path.dirname(small), exist_ok=True)
                        im.save(small)
                        tex = CoreImage(small).texture
                    except Exception:
                        buf = io.BytesIO()
                        im.save(buf, 'PNG')
                        buf.seek(0)
                        tex = CoreImage(buf, ext='png').texture
        except Exception:
            tex = None
    _icon_cache[key] = tex
    return tex


def contrast(c):
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return BLACK if lum > 0.55 else WHITE


def paint_bg(widget, rgba, radius=0):
    with widget.canvas.before:
        Color(*rgba)
        r = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda w, v: setattr(r, 'pos', v),
                size=lambda w, v: setattr(r, 'size', v))
    return r


def bind_text_size(label):
    label.bind(size=lambda w, s: setattr(w, 'text_size', s))
    return label


# --------------------------------------------------------------------------
# Generic UI pieces
# --------------------------------------------------------------------------
class RoundButton(ButtonBehavior, Label):
    """Rounded button. Optional icon drawn in its own colors.
    icon_only=True hides the text when the icon file exists
    (if the file is missing, the text is shown instead)."""

    def __init__(self, bg=YELLOW, fg=BLACK, radius=12, outline=None,
                 icon=None, icon_only=False, icon_scale=None, **kw):
        kw.setdefault('bold', True)
        kw.setdefault('font_size', sp(15))
        kw.setdefault('shorten', True)
        has_icon = icon_exists(icon)
        ftext = kw.get('text', '')
        halign = 'center'
        if has_icon:
            if icon_only:
                kw['text'] = ''
            else:
                halign = 'left'
        super().__init__(color=fg, halign=halign, valign='middle', **kw)
        self._iname = icon if has_icon else None
        self._iscale = icon_scale
        self._ipx = 0
        self._ftext = ftext
        self._bg = list(bg)
        self._r = dp(radius)
        with self.canvas.before:
            self._col = Color(*self._bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[self._r])
            Color(*(outline if outline else (0, 0, 0, 0)))
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                 self.height, self._r),
                              width=dp(1.4))
        if self._iname:
            with self.canvas.after:
                self._icol = Color(1, 1, 1, 1)
                self._irect = Rectangle(pos=self.pos, size=(0, 0))
        self.bind(pos=self._upd, size=self._upd, state=self._upd,
                  color=self._upd)
        self.bind(size=lambda w, s: setattr(w, 'text_size', s))
        self._upd()

    @property
    def _itex(self):          # used by the "recent files" list
        return True if self._iname else None

    def _upd(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width,
                                        self.height, self._r)
        r, g, b, al = self._bg
        k = 0.8 if self.state == 'down' else 1.0
        self._col.rgba = (r * k, g * k, b * k, al)
        if not self._iname:
            return
        scale = self._iscale or ICON_SCALE.get(self._iname,
                                               DEFAULT_ICON_SCALE)
        side = min(self.width, self.height) * scale
        if side < 4:
            return
        want = max(32, int(math.ceil(side / 16.0)) * 16)
        if want != self._ipx:
            self._ipx = want
            tex = icon_tex(self._iname, want)
            if tex is None:                      # broken file -> back to text
                self._iname = None
                self._irect.size = (0, 0)
                self.text = self._ftext
                self.halign = 'center'
                self.padding_x = 0
                return
            self._irect.texture = tex
        self._icol.rgba = self.color if TINT_ICONS else (1, 1, 1, 1)
        if self.text:
            gap = dp(14)
            self._irect.pos = (self.x + gap,
                               self.y + (self.height - side) / 2.0)
            self.padding_x = gap * 2 + side
        else:
            self._irect.pos = (self.center_x - side / 2.0,
                               self.center_y - side / 2.0)
        self._irect.size = (side, side)

    def set_style(self, bg=None, fg=None):
        if bg is not None:
            self._bg = list(bg)
        if fg is not None:
            self.color = fg
        self._upd()


class IconImage(Widget):
    """Fixed-size icon picture (home cards, logo, folder icon)."""

    def __init__(self, name, tint=(1, 1, 1, 1), size_dp=None, **kw):
        s = dp(size_dp or ICON_DP.get(name, 48))
        super().__init__(size_hint=(None, None), size=(s, s), **kw)
        self.tint = tint
        self.tex = icon_tex(name, s)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *a):
        self.canvas.clear()
        if self.tex is None:
            return
        with self.canvas:
            Color(*(self.tint if TINT_ICONS else (1, 1, 1, 1)))
            Rectangle(texture=self.tex, pos=self.pos, size=self.size)


class Dlg(Popup):
    def __init__(self, **kw):
        kw.setdefault('background', '')
        kw.setdefault('background_color', (0.08, 0.08, 0.08, 1))
        kw.setdefault('separator_color', YELLOW)
        kw.setdefault('title_color', YELLOW)
        kw.setdefault('auto_dismiss', False)
        super().__init__(**kw)


def toast(text, dur=1.6):
    lab = Label(text=text, size_hint=(None, None), color=BLACK, bold=True,
                font_size=sp(14))
    lab.texture_update()
    lab.size = (lab.texture_size[0] + dp(36), dp(40))
    lab.pos = ((Window.width - lab.width) / 2, dp(90))
    paint_bg(lab, YELLOW, dp(20))
    Window.add_widget(lab)
    Clock.schedule_once(lambda dt: Window.remove_widget(lab), dur)


def ask(title, msg, options, height=190):
    """options: list of (label, callback or None). First one is highlighted."""
    box = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(10))
    lab = bind_text_size(Label(text=msg, color=WHITE, halign='center',
                               valign='middle'))
    box.add_widget(lab)
    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
    box.add_widget(row)
    pop = Dlg(title=title, content=box, size_hint=(.88, None),
              height=dp(height))

    def make(f):
        def cb(*_):
            pop.dismiss()
            if f:
                f()
        return cb

    for i, (text, fn) in enumerate(options):
        b = RoundButton(text=text, bg=YELLOW if i == 0 else DARK2,
                        fg=BLACK if i == 0 else WHITE)
        b.bind(on_release=make(fn))
        row.add_widget(b)
    pop.open()


def text_prompt(title, initial, cb, hint=''):
    box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
    ti = TextInput(text=initial, multiline=True, hint_text=hint,
                   font_size=sp(18), background_normal='',
                   background_active='', background_color=WHITE,
                   foreground_color=BLACK, cursor_color=BLACK)
    box.add_widget(ti)
    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
    ok = RoundButton(text='OK')
    cancel = RoundButton(text='Cancel', bg=DARK2, fg=WHITE)
    row.add_widget(ok)
    row.add_widget(cancel)
    box.add_widget(row)
    pop = Dlg(title=title, content=box, size_hint=(.92, .5))

    def done(*_):
        pop.dismiss()
        cb(ti.text)

    ok.bind(on_release=done)
    cancel.bind(on_release=lambda *_: pop.dismiss())
    pop.open()
    Clock.schedule_once(lambda dt: setattr(ti, 'focus', True), .3)


def pick_color(initial, cb):
    outer = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
    grid = GridLayout(cols=4, spacing=dp(8))
    pop = Dlg(title='Choose color', content=outer, size_hint=(.92, None),
              height=dp(330))

    def choose(c):
        pop.dismiss()
        cb(list(c))

    for hx in PALETTE:
        c = get_color_from_hex(hx)
        b = RoundButton(text='', bg=c, outline=(0.6, 0.6, 0.6, 1), radius=10)
        b.bind(on_release=lambda *_, c=c: choose(c))
        grid.add_widget(b)
    outer.add_widget(grid)
    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
    custom = RoundButton(text='Custom...')
    cancel = RoundButton(text='Cancel', bg=DARK2, fg=WHITE)
    row.add_widget(custom)
    row.add_widget(cancel)
    outer.add_widget(row)

    def go_custom(*_):
        pop.dismiss()
        custom_picker(initial, cb)

    custom.bind(on_release=go_custom)
    cancel.bind(on_release=lambda *_: pop.dismiss())
    pop.open()


def custom_picker(initial, cb):
    box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(6))
    cp = ColorPicker(color=list(initial))
    box.add_widget(cp)
    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
    ok = RoundButton(text='OK')
    cancel = RoundButton(text='Cancel', bg=DARK2, fg=WHITE)
    row.add_widget(ok)
    row.add_widget(cancel)
    box.add_widget(row)
    pop = Dlg(title='Custom color', content=box, size_hint=(.96, .92))

    def done(*_):
        pop.dismiss()
        cb(list(cp.color))

    ok.bind(on_release=done)
    cancel.bind(on_release=lambda *_: pop.dismiss())
    pop.open()


# --------------------------------------------------------------------------
# Files / storage
# --------------------------------------------------------------------------
def request_android_permissions():
    if platform != 'android':
        return
    try:
        from android.permissions import Permission, request_permissions
        request_permissions([Permission.READ_EXTERNAL_STORAGE,
                             Permission.WRITE_EXTERNAL_STORAGE])
    except Exception:
        pass


def storage_dir():
    cands = []
    if platform == 'android':
        try:
            from android.storage import primary_external_storage_path
            cands.append(os.path.join(primary_external_storage_path(),
                                      'Documents', 'NoteBook'))
        except Exception:
            pass
    else:
        cands.append(os.path.join(os.path.expanduser('~'), 'NoteBook'))
    cands.append(App.get_running_app().user_data_dir)
    for c in cands:
        try:
            os.makedirs(c, exist_ok=True)
            if os.access(c, os.W_OK):
                return c
        except Exception:
            continue
    return os.getcwd()


def stamp():
    return time.strftime('%Y%m%d_%H%M%S')


def load_image_bytes(path, max_side=1280):
    ext = os.path.splitext(path)[1].lower().lstrip('.') or 'png'
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        from PIL import Image as PILImage
        from PIL import ImageOps
        im = PILImage.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        if max(im.size) > max_side:
            im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        if im.mode in ('RGBA', 'LA', 'P'):
            im.convert('RGBA').save(buf, 'PNG')
            return buf.getvalue(), 'png'
        im.convert('RGB').save(buf, 'JPEG', quality=88)
        return buf.getvalue(), 'jpg'
    except Exception:
        return raw, ('jpg' if ext == 'jpeg' else ext)


class FileDialog(Dlg):
    def __init__(self, title, mode, exts, callback, start_dir=None,
                 default_name='', **kw):
        super().__init__(title=title, size_hint=(.96, .9), **kw)
        self.mode = mode
        self.exts = tuple(e.lower() for e in exts)
        self.callback = callback
        start = start_dir if (start_dir and os.path.isdir(start_dir)) \
            else storage_dir()
        box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        up = RoundButton(text='Up', icon='folder_up', icon_only=True,
                         size_hint_x=None, width=dp(52))
        up.bind(on_release=self._up)
        top.add_widget(up)
        fi = IconImage('folder', tint=YELLOW)
        if fi.tex is not None:
            fi.pos_hint = {'center_y': .5}
            top.add_widget(fi)
        self.path_lbl = bind_text_size(Label(
            text=start, color=GREY, halign='left', valign='middle',
            shorten=True, shorten_from='left', font_size=sp(12)))
        top.add_widget(self.path_lbl)
        box.add_widget(top)
        self.fc = FileChooserListView(path=start, filters=[self._filter],
                                      dirselect=False)
        self.fc.bind(path=self._on_path, selection=self._on_sel,
                     on_submit=self._on_submit)
        box.add_widget(self.fc)
        self.name = None
        if mode == 'save':
            self.name = TextInput(text=default_name, multiline=False,
                                  size_hint_y=None, height=dp(44),
                                  font_size=sp(16), background_normal='',
                                  background_active='', background_color=WHITE,
                                  foreground_color=BLACK, cursor_color=BLACK)
            box.add_widget(self.name)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        ok = RoundButton(text='Save' if mode == 'save' else 'Open',
                         icon='save' if mode == 'save' else 'open')
        cancel = RoundButton(text='Cancel', icon='close', bg=DARK2, fg=WHITE)
        ok.bind(on_release=self._ok)
        cancel.bind(on_release=lambda *_: self.dismiss())
        row.add_widget(ok)
        row.add_widget(cancel)
        box.add_widget(row)
        self.content = box

    def _filter(self, folder, name):
        return name.lower().endswith(self.exts)

    def _up(self, *_):
        self.fc.path = os.path.dirname(self.fc.path.rstrip(os.sep)) or os.sep

    def _on_path(self, fc, p):
        self.path_lbl.text = p

    def _on_sel(self, fc, sel):
        if self.mode == 'save' and sel:
            self.name.text = os.path.basename(sel[0])

    def _on_submit(self, fc, sel, touch):
        if self.mode == 'open' and sel:
            self._finish(sel[0])

    def _ok(self, *_):
        if self.mode == 'open':
            if self.fc.selection:
                self._finish(self.fc.selection[0])
        else:
            n = self.name.text.strip()
            if not n:
                return
            if not n.lower().endswith(self.exts[0]):
                n += self.exts[0]
            self._finish(os.path.join(self.fc.path, n))

    def _finish(self, path):
        self.dismiss()
        self.callback(path)


class DocMixin:
    def guard(self, proceed):
        if not self.dirty:
            proceed()
            return
        ask('Unsaved changes', 'Do you want to save your changes first?',
            [('Save', lambda: self.save(then=proceed)),
             ('Discard', proceed), ('Cancel', None)])


# --------------------------------------------------------------------------
# Home screen
# --------------------------------------------------------------------------
class Icon(Widget):
    """Vector fallback used only when the card PNG icon is missing."""

    def __init__(self, kind, color, **kw):
        super().__init__(size_hint=(None, None), size=(dp(54), dp(54)), **kw)
        self.kind = kind
        self.col = color
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *a):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas:
            Color(*self.col)
            if self.kind == 'note':
                Line(rounded_rectangle=(x + w * .12, y, w * .76, h, dp(6)),
                     width=dp(2))
                for i in range(3):
                    yy = y + h * (.28 + .22 * i)
                    Line(points=[x + w * .28, yy, x + w * .72, yy],
                         width=dp(2), cap='round')
            else:
                Line(bezier=[x, y + h * .3, x + w * .3, y + h,
                             x + w * .6, y - h * .1, x + w, y + h * .75],
                     width=dp(2.6))
                Ellipse(pos=(x + w * .78, y + h * .62), size=(dp(9), dp(9)))


def card_icon(name, fallback_kind, color):
    ic = IconImage(name, tint=color)
    return ic if ic.tex is not None else Icon(fallback_kind, color)


class Card(ButtonBehavior, BoxLayout):
    def __init__(self, title, sub, bg, fg, icon_name, fallback_kind, **kw):
        super().__init__(orientation='vertical', padding=dp(18),
                         spacing=dp(4), **kw)
        paint_bg(self, bg, dp(22))
        row = BoxLayout(size_hint_y=None, height=dp(64))
        row.add_widget(card_icon(icon_name, fallback_kind, fg))
        row.add_widget(Widget())
        self.add_widget(row)
        self.add_widget(Widget())
        self.add_widget(bind_text_size(Label(
            text=title, font_size=sp(26), bold=True, color=fg, halign='left',
            valign='bottom', size_hint_y=None, height=dp(38))))
        self.add_widget(bind_text_size(Label(
            text=sub, font_size=sp(13), color=fg, halign='left',
            valign='top', size_hint_y=None, height=dp(34))))
        self.bind(state=lambda w, s: setattr(w, 'opacity',
                                             .85 if s == 'down' else 1))


class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='home', **kw)
        root = BoxLayout(orientation='vertical')
        paint_bg(root, WHITE)
        head = BoxLayout(size_hint_y=None, height=dp(120),
                         padding=[dp(22), dp(16), dp(18), dp(16)],
                         spacing=dp(10))
        paint_bg(head, BLACK)
        titles = BoxLayout(orientation='vertical')
        titles.add_widget(bind_text_size(Label(
            text='NoteBook', font_size=sp(34), bold=True, color=YELLOW,
            halign='left', valign='bottom')))
        titles.add_widget(bind_text_size(Label(
            text='Write. Sketch. Keep it light.', font_size=sp(14),
            color=WHITE, halign='left', valign='top',
            size_hint_y=None, height=dp(26))))
        head.add_widget(titles)
        logo = IconImage('app_icon')
        if logo.tex is not None:
            logo.pos_hint = {'center_y': .5}
            head.add_widget(logo)
        root.add_widget(head)
        strip = Widget(size_hint_y=None, height=dp(5))
        paint_bg(strip, YELLOW)
        root.add_widget(strip)

        body = BoxLayout(orientation='vertical', padding=dp(16),
                         spacing=dp(12))
        c1 = Card('Notebook', 'Write plain text notes, saved as .txt',
                  YELLOW, BLACK, 'note_card', 'note')
        c1.bind(on_release=lambda *_: App.get_running_app().new_notes())
        c2 = Card('Drawing Studio', 'Draw, add text and images, saved as .nbl',
                  BLACK, YELLOW, 'draw_card', 'draw')
        c2.bind(on_release=lambda *_: App.get_running_app().new_drawing())
        body.add_widget(c1)
        body.add_widget(c2)
        ob = RoundButton(text='Open file', icon='open', bg=WHITE, fg=BLACK,
                         outline=BLACK, size_hint_y=None, height=dp(52))
        ob.bind(on_release=self.open_file)
        body.add_widget(ob)
        body.add_widget(bind_text_size(Label(
            text='Recent', bold=True, color=BLACK, halign='left',
            valign='middle', size_hint_y=None, height=dp(26))))
        self.recent_box = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        self.recent_box.bind(minimum_height=self.recent_box.setter('height'))
        sv = ScrollView(size_hint_y=None, height=dp(140), bar_width=dp(3))
        sv.add_widget(self.recent_box)
        body.add_widget(sv)
        root.add_widget(body)
        self.add_widget(root)

    def on_pre_enter(self, *a):
        self.refresh_recent()

    def refresh_recent(self):
        box = self.recent_box
        box.clear_widgets()
        items = App.get_running_app().get_recent()
        if not items:
            box.add_widget(Label(text='No recent files yet', color=GREY,
                                 size_hint_y=None, height=dp(40)))
        for it in items[:6]:
            is_txt = it['kind'] == 'txt'
            tag = 'TXT' if is_txt else 'NBL'
            b = RoundButton(text=os.path.basename(it['path']),
                            icon='file_txt' if is_txt else 'file_nbl',
                            bg=LIGHT, fg=BLACK, bold=False, font_size=sp(14),
                            size_hint_y=None, height=dp(42))
            if b._itex is None:
                b.text = '%s    %s' % (tag, os.path.basename(it['path']))
            b.bind(on_release=lambda *_, p=it['path']:
                   App.get_running_app().open_path(p))
            box.add_widget(b)

    def open_file(self, *_):
        FileDialog('Open file', 'open', ['.txt', '.nbl'],
                   lambda p: App.get_running_app().open_path(p)).open()


# --------------------------------------------------------------------------
# Notebook screen (.txt)
# --------------------------------------------------------------------------
class NotesScreen(DocMixin, Screen):
    def __init__(self, **kw):
        super().__init__(name='notes', **kw)
        self.path = None
        self.dirty = False
        self._loading = False
        root = BoxLayout(orientation='vertical')
        paint_bg(root, WHITE)

        top = BoxLayout(size_hint_y=None, height=dp(54),
                        padding=[dp(8), dp(7)], spacing=dp(8))
        paint_bg(top, BLACK)
        back = RoundButton(text='Back', icon='back', icon_only=True,
                           size_hint_x=None, width=dp(54))
        back.bind(on_release=lambda *_: self.back())
        self.title = bind_text_size(Label(
            text='Untitled.txt', color=WHITE, bold=True, halign='left',
            valign='middle', shorten=True, shorten_from='right',
            font_size=sp(16)))
        sv = RoundButton(text='Save', icon='save', icon_only=True,
                         size_hint_x=None, width=dp(54))
        sv.bind(on_release=lambda *_: self.save())
        top.add_widget(back)
        top.add_widget(self.title)
        top.add_widget(sv)
        root.add_widget(top)

        self.ti = TextInput(
            hint_text='Start writing...', multiline=True, font_size=sp(17),
            background_normal='', background_active='', background_color=WHITE,
            foreground_color=BLACK, hint_text_color=GREY,
            cursor_color=get_color_from_hex('#E0A800'),
            selection_color=(1, .77, 0, .4), padding=[dp(14)] * 4,
            write_tab=False)
        self.ti.bind(text=self._on_text)
        root.add_widget(self.ti)

        bottom = BoxLayout(size_hint_y=None, height=dp(50),
                           padding=[dp(8), dp(6)], spacing=dp(6))
        paint_bg(bottom, DARK)

        def add(text, icon, fn, w=46):
            b = RoundButton(text=text, icon=icon, icon_only=True, bg=DARK2,
                            fg=WHITE, size_hint_x=None, width=dp(w),
                            font_size=sp(13), radius=10)
            b.bind(on_release=lambda *_: fn())
            bottom.add_widget(b)

        add('New', 'new', lambda: self.guard(self.new_doc))
        add('Open', 'open', self.open_action)
        add('Save As', 'save_as', self.save_as)
        add('A-', 'font_smaller', lambda: self.font(-1))
        add('A+', 'font_larger', lambda: self.font(+1))
        self.count = Label(text='0 words', color=GREY, font_size=sp(12))
        bottom.add_widget(self.count)
        root.add_widget(bottom)
        self.add_widget(root)

    def font(self, d):
        self.ti.font_size = min(max(self.ti.font_size + d * sp(2), sp(11)),
                                sp(40))

    def _on_text(self, *a):
        self.count.text = '%d words' % len(self.ti.text.split())
        if not self._loading:
            self.dirty = True
        self._title()

    def _title(self):
        name = os.path.basename(self.path) if self.path else 'Untitled.txt'
        self.title.text = name + (' *' if self.dirty else '')

    def new_doc(self):
        self._loading = True
        self.ti.text = ''
        self._loading = False
        self.path = None
        self.dirty = False
        self._title()

    def open_action(self):
        def pick(p):
            self.load(p)
        self.guard(lambda: FileDialog('Open note', 'open', ['.txt'], pick).open())

    def load(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                txt = f.read()
        except Exception as e:
            ask('Cannot open file', str(e), [('OK', None)])
            return False
        self._loading = True
        self.ti.text = txt
        self._loading = False
        self.ti.cursor = (0, 0)
        self.path = path
        self.dirty = False
        self._title()
        App.get_running_app().add_recent(path, 'txt')
        return True

    def save(self, then=None):
        if self.path:
            if self._write(self.path) and then:
                then()
        else:
            self.save_as(then)

    def save_as(self, then=None):
        name = os.path.basename(self.path) if self.path else 'note_%s.txt' % stamp()
        start = os.path.dirname(self.path) if self.path else None

        def cb(p):
            self.path = p
            if self._write(p) and then:
                then()
        FileDialog('Save note', 'save', ['.txt'], cb, start_dir=start,
                   default_name=name).open()

    def _write(self, p):
        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.ti.text)
        except Exception as e:
            ask('Cannot save file', str(e), [('OK', None)])
            return False
        self.dirty = False
        self._title()
        App.get_running_app().add_recent(p, 'txt')
        toast('Saved')
        return True

    def back(self):
        self.guard(lambda: setattr(App.get_running_app().sm, 'current', 'home'))


# --------------------------------------------------------------------------
# Drawing model
# --------------------------------------------------------------------------
def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class Stroke:
    def __init__(self, kind, color, width, pts):
        self.kind = kind
        self.color = list(color)
        self.width = width
        self.pts = list(pts)
        self.gfx = None

    def poly(self):
        p = self.pts
        if self.kind == 'pen':
            return p if len(p) >= 4 else [p[0], p[1], p[0] + .1, p[1]]
        x1, y1, x2, y2 = p[0], p[1], p[-2], p[-1]
        if self.kind == 'line':
            return [x1, y1, x2, y2]
        if self.kind == 'rect':
            return [x1, y1, x2, y1, x2, y2, x1, y2, x1, y1]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        rx, ry = abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0
        out = []
        n = 64
        for i in range(n + 1):
            a = 2 * math.pi * i / n
            out += [cx + rx * math.cos(a), cy + ry * math.sin(a)]
        return out

    def hit(self, x, y, r):
        poly = self.poly()
        rr = r + self.width / 2.0
        for i in range(0, len(poly) - 2, 2):
            if seg_dist(x, y, poly[i], poly[i + 1], poly[i + 2], poly[i + 3]) <= rr:
                return True
        return False

    def to_dict(self, k):
        return {'kind': self.kind, 'color': self.color,
                'width': round(self.width / k, 2),
                'pts': [round(v / k, 2) for v in self.pts]}

    @classmethod
    def from_dict(cls, d, k):
        return cls(d['kind'], d['color'], d['width'] * k,
                   [v * k for v in d['pts']])


class CanvasObject(Widget):
    """Movable / resizable object placed on the drawing page."""
    selected = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), **kw)
        self._mode = None
        self._before = None
        self._geo = (0, 0, 1, 1)
        self._fs0 = 0
        self.bind(pos=self._sel_draw, size=self._sel_draw,
                  selected=self._sel_draw)

    def _sel_draw(self, *a):
        self.canvas.after.clear()
        if not self.selected:
            return
        h = HANDLE
        with self.canvas.after:
            Color(*YELLOW)
            Line(rectangle=(self.x, self.y, self.width, self.height),
                 width=dp(1.5))
            Rectangle(pos=(self.right - h / 2, self.y - h / 2), size=(h, h))
            Color(*BLACK)
            Line(rectangle=(self.right - h / 2, self.y - h / 2, h, h),
                 width=dp(1.2))

    def collide_point(self, x, y):
        if super().collide_point(x, y):
            return True
        return self.selected and abs(x - self.right) <= HANDLE and \
            abs(y - self.y) <= HANDLE

    def on_touch_down(self, touch):
        cv = self.parent
        if cv is None or getattr(cv, 'tool', '') != 'select':
            return False
        if not self.collide_point(*touch.pos):
            return False
        near = self.selected and abs(touch.x - self.right) <= HANDLE * .8 \
            and abs(touch.y - self.y) <= HANDLE * .8
        cv.select(self)
        touch.grab(self)
        self._before = self.snapshot()
        self._mode = 'resize' if near else 'move'
        self._start = (touch.x, touch.y)
        self._geo = (self.x, self.top, self.width, self.height)
        self._fs0 = getattr(self, 'font_size', 0)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        dx, dy = touch.x - self._start[0], touch.y - self._start[1]
        if self._mode == 'move':
            self.pos = (self._geo[0] + dx, self._geo[1] - self._geo[3] + dy)
        else:
            self.resize_drag(dx, dy)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        after = self.snapshot()
        if self.parent is not None and after != self._before:
            self.parent.push(('modify', self, self._before, after))
        self._mode = None
        return True


class TextObject(CanvasObject, Label):
    def __init__(self, raw='', font_size=None, color=(0, 0, 0, 1), bold=False,
                 italic=False, underline=False, tl=None, **kw):
        super().__init__(markup=True, **kw)
        self.raw = raw
        self.u = underline
        self.font_size = font_size or dp(24)
        self.color = list(color)
        self.bold = bold
        self.italic = italic
        self._pending = tl
        self.refresh()

    def refresh(self):
        t = escape_markup(self.raw)
        if self.u:
            t = '[u]%s[/u]' % t
        self.text = t
        self.texture_update()
        self._fit()

    def _fit(self):
        tw, th = self.texture_size
        pad = dp(6)
        if self._pending:
            x, top = self._pending
            self._pending = None
        else:
            x, top = self.x, self.top
        self.size = (max(tw, dp(10)) + 2 * pad, max(th, dp(10)) + 2 * pad)
        self.x = x
        self.top = top

    def snapshot(self):
        return dict(raw=self.raw, fs=self.font_size, color=list(self.color),
                    bold=self.bold, italic=self.italic, u=self.u,
                    x=self.x, top=self.top)

    def apply(self, d):
        self.raw = d['raw']
        self.font_size = d['fs']
        self.color = list(d['color'])
        self.bold = d['bold']
        self.italic = d['italic']
        self.u = d['u']
        self._pending = (d['x'], d['top'])
        self.refresh()

    def mutate(self, **ch):
        before = self.snapshot()
        for k, v in ch.items():
            setattr(self, k, v)
        self._pending = (self.x, self.top)
        self.refresh()
        return before, self.snapshot()

    def resize_drag(self, dx, dy):
        x0, top0, w0, h0 = self._geo
        f = max(0.2, (w0 + dx) / float(w0))
        self.font_size = min(max(self._fs0 * f, dp(8)), dp(400))
        self._pending = (x0, top0)
        self.refresh()

    def to_dict(self, cv, k):
        return {'type': 'text', 'text': self.raw, 'font': self.font_size / k,
                'color': list(self.color), 'bold': self.bold,
                'italic': self.italic, 'underline': self.u,
                'x': (self.x - cv.x) / k, 'top': (self.top - cv.y) / k}

    @classmethod
    def from_dict(cls, cv, d, k):
        return cls(d['text'], font_size=d['font'] * k, color=d['color'],
                   bold=d.get('bold', False), italic=d.get('italic', False),
                   underline=d.get('underline', False),
                   tl=(cv.x + d['x'] * k, cv.y + d['top'] * k))


class ImageObject(CanvasObject):
    def __init__(self, data, ext='png', **kw):
        super().__init__(**kw)
        self.data = data
        self.ext = ext
        self.tex = CoreImage(io.BytesIO(data), ext=ext).texture
        self.aspect = self.tex.height / float(self.tex.width) if self.tex.width else 1.0
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self.tex, pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)
        self.size = (dp(200), dp(200) * self.aspect)

    def _sync(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def snapshot(self):
        return dict(x=self.x, top=self.top, w=self.width, h=self.height)

    def apply(self, d):
        self.size = (d['w'], d['h'])
        self.x = d['x']
        self.top = d['top']

    def resize_drag(self, dx, dy):
        x0, top0, w0, h0 = self._geo
        w = max(dp(30), w0 + dx)
        self.size = (w, w * self.aspect)
        self.x = x0
        self.top = top0

    def to_dict(self, cv, k):
        return {'type': 'image', 'ext': self.ext,
                'data': base64.b64encode(self.data).decode('ascii'),
                'x': (self.x - cv.x) / k, 'top': (self.top - cv.y) / k,
                'w': self.width / k, 'h': self.height / k}

    @classmethod
    def from_dict(cls, cv, d, k):
        o = cls(base64.b64decode(d['data']), d.get('ext', 'png'))
        o.size = (d['w'] * k, d['h'] * k)
        o.x = cv.x + d['x'] * k
        o.top = cv.y + d['top'] * k
        return o


class DrawCanvas(FloatLayout):
    tool = StringProperty('pen')
    color = ListProperty([0.07, 0.07, 0.07, 1])
    brush = NumericProperty(4)          # in dp
    selected = ObjectProperty(None, allownone=True)

    def __init__(self, screen, **kw):
        super().__init__(**kw)
        self.screen = screen
        self.strokes = []
        self.undo_stack = []
        self.redo_stack = []
        self.bg_color = [1, 1, 1, 1]
        self._cur = None
        self._erased = []
        self._last_pos = (0, 0)
        with self.canvas.before:
            self._bgc = Color(*self.bg_color)
            self._bgr = Rectangle(pos=self.pos, size=self.size)
        self._tr = Translate(0, 0)
        self._sg = InstructionGroup()
        self.canvas.add(PushMatrix())
        self.canvas.add(self._tr)
        self.canvas.add(self._sg)
        self.canvas.add(PopMatrix())
        self.bind(pos=self._geom, size=self._geom)

    # ---- geometry ----
    def _geom(self, *a):
        self._bgr.pos = self.pos
        self._bgr.size = self.size
        self._tr.xy = self.pos
        dx = self.x - self._last_pos[0]
        dy = self.y - self._last_pos[1]
        if dx or dy:
            for o in self.objects():
                o.pos = (o.x + dx, o.y + dy)
        self._last_pos = tuple(self.pos)

    def set_bg(self, c):
        self.bg_color = list(c)
        self._bgc.rgba = self.bg_color

    def objects(self):
        return [c for c in reversed(self.children) if isinstance(c, CanvasObject)]

    # ---- stroke graphics ----
    def _gfx_add(self, s):
        c = Color(*s.color)
        l = Line(points=s.poly(), width=s.width, cap='round', joint='round')
        self._sg.add(c)
        self._sg.add(l)
        s.gfx = (c, l)

    def _gfx_del(self, s):
        if s.gfx:
            for i in s.gfx:
                self._sg.remove(i)
            s.gfx = None

    # ---- selection ----
    def select(self, obj):
        if self.selected is obj:
            return
        if self.selected is not None:
            self.selected.selected = False
        self.selected = obj
        if obj is not None:
            obj.selected = True
        self.screen.refresh_props()

    def add_obj(self, o):
        self.add_widget(o)

    def remove_obj(self, o):
        if self.selected is o:
            self.select(None)
        self.remove_widget(o)

    def bring_front(self, o):
        self.remove_widget(o)
        self.add_widget(o)

    # ---- undo / redo ----
    def push(self, action):
        self.undo_stack.append(action)
        self.redo_stack = []
        self.screen.touch_dirty()

    def undo(self):
        if self.undo_stack:
            a = self.undo_stack.pop()
            self._apply(a, True)
            self.redo_stack.append(a)
            self.screen.touch_dirty()

    def redo(self):
        if self.redo_stack:
            a = self.redo_stack.pop()
            self._apply(a, False)
            self.undo_stack.append(a)
            self.screen.touch_dirty()

    def _drop(self, strokes):
        for s in strokes:
            if s in self.strokes:
                self.strokes.remove(s)
            self._gfx_del(s)

    def _restore(self, strokes):
        for s in strokes:
            self.strokes.append(s)
            self._gfx_add(s)

    def _apply(self, a, undo):
        k = a[0]
        if k == 'stroke':
            (self._drop if undo else self._restore)([a[1]])
        elif k == 'erase':
            (self._restore if undo else self._drop)(a[1])
        elif k == 'obj':
            (self.remove_obj if undo else self.add_obj)(a[1])
        elif k == 'delobj':
            (self.add_obj if undo else self.remove_obj)(a[1])
        elif k == 'modify':
            a[1].apply(a[2] if undo else a[3])
        elif k == 'clear':
            if undo:
                self._restore(a[1])
                for o in a[2]:
                    self.add_obj(o)
            else:
                self._drop(list(a[1]))
                for o in a[2]:
                    self.remove_obj(o)

    # ---- whole page ----
    def clear_all(self, record=True):
        self.select(None)
        strokes = list(self.strokes)
        objs = self.objects()
        for s in strokes:
            self._gfx_del(s)
        self.strokes = []
        for o in objs:
            self.remove_widget(o)
        if record and (strokes or objs):
            self.push(('clear', strokes, objs))

    def reset(self):
        self.clear_all(False)
        self.undo_stack = []
        self.redo_stack = []
        self.set_bg([1, 1, 1, 1])

    def to_dict(self):
        k = dp(1)
        return {'app': 'NoteBook', 'format': 'nbl', 'version': 1,
                'bg': self.bg_color,
                'size': [self.width / k, self.height / k],
                'strokes': [s.to_dict(k) for s in self.strokes],
                'objects': [o.to_dict(self, k) for o in self.objects()]}

    def load_dict(self, d):
        self.reset()
        k = dp(1)
        self.set_bg(d.get('bg', [1, 1, 1, 1]))
        for sd in d.get('strokes', []):
            s = Stroke.from_dict(sd, k)
            self.strokes.append(s)
            self._gfx_add(s)
        for od in d.get('objects', []):
            try:
                if od['type'] == 'text':
                    o = TextObject.from_dict(self, od, k)
                elif od['type'] == 'image':
                    o = ImageObject.from_dict(self, od, k)
                else:
                    continue
            except Exception:
                continue
            self.add_widget(o)

    # ---- touch handling ----
    def _erase_at(self, x, y):
        r = dp(10)
        for s in self.strokes[:]:
            if s.hit(x, y, r):
                self.strokes.remove(s)
                self._gfx_del(s)
                self._erased.append(s)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if self.tool == 'select':
            if super().on_touch_down(touch):
                return True
            self.select(None)
            return True
        x, y = touch.x - self.x, touch.y - self.y
        if self.tool == 'text':
            self.screen.ask_text(touch.x, touch.y)
            return True
        touch.grab(self)
        if self.tool == 'eraser':
            self._erased = []
            self._erase_at(x, y)
        else:
            pts = [x, y] if self.tool == 'pen' else [x, y, x, y]
            s = Stroke(self.tool, self.color, dp(self.brush), pts)
            self._cur = s
            self._gfx_add(s)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            x, y = touch.x - self.x, touch.y - self.y
            if self.tool == 'eraser':
                self._erase_at(x, y)
            elif self._cur is not None:
                s = self._cur
                if self.tool == 'pen':
                    if math.hypot(x - s.pts[-2], y - s.pts[-1]) < dp(1.5):
                        return True
                    s.pts += [x, y]
                else:
                    s.pts = [s.pts[0], s.pts[1], x, y]
                s.gfx[1].points = s.poly()
            return True
        if self.tool == 'select':
            return super().on_touch_move(touch)
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._cur is not None:
                s = self._cur
                self._cur = None
                tiny = abs(s.pts[-2] - s.pts[0]) + abs(s.pts[-1] - s.pts[1]) < dp(3)
                if s.kind != 'pen' and tiny:
                    self._gfx_del(s)
                else:
                    self.strokes.append(s)
                    self.push(('stroke', s))
            if self._erased:
                self.push(('erase', self._erased))
                self._erased = []
            return True
        if self.tool == 'select':
            return super().on_touch_up(touch)
        return False


# --------------------------------------------------------------------------
# Drawing screen (.nbl)
# --------------------------------------------------------------------------
class DrawScreen(DocMixin, Screen):
    TOOLS = [('pen', 'Pen'), ('line', 'Line'), ('rect', 'Rect'),
             ('oval', 'Oval'), ('eraser', 'Erase'), ('text', 'Text'),
             ('select', 'Select')]

    def __init__(self, **kw):
        super().__init__(name='draw', **kw)
        self.path = None
        self.dirty = False
        self.text_size = dp(24)
        root = BoxLayout(orientation='vertical')
        paint_bg(root, DARK)

        top = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(8), dp(6)], spacing=dp(6))
        paint_bg(top, BLACK)

        def tb(text, icon, fn, w=46, bg=YELLOW, fg=BLACK):
            b = RoundButton(text=text, icon=icon, icon_only=True, bg=bg,
                            fg=fg, size_hint_x=None, width=dp(w),
                            font_size=sp(13), radius=10)
            b.bind(on_release=lambda *_: fn())
            return b

        top.add_widget(tb('Back', 'back', self.back, 52))
        self.title = bind_text_size(Label(
            text='Untitled.nbl', color=WHITE, bold=True, halign='left',
            valign='middle', shorten=True, shorten_from='right',
            font_size=sp(15)))
        top.add_widget(self.title)
        top.add_widget(tb('Undo', 'undo', lambda: self.cv.undo(), 46, DARK2, WHITE))
        top.add_widget(tb('Redo', 'redo', lambda: self.cv.redo(), 46, DARK2, WHITE))
        top.add_widget(tb('Menu', 'menu', self.open_menu, 46))
        root.add_widget(top)

        self.cv = DrawCanvas(self)
        root.add_widget(self.cv)

        self.prop_box = GridLayout(rows=1, size_hint_x=None, spacing=dp(6),
                                   padding=[dp(8), dp(5)])
        self.prop_box.bind(minimum_width=self.prop_box.setter('width'))
        psv = ScrollView(size_hint_y=None, height=dp(50), do_scroll_y=False,
                         bar_width=0)
        psv.add_widget(self.prop_box)
        paint_bg(psv, DARK)
        root.add_widget(psv)

        tools = GridLayout(rows=1, size_hint_x=None, spacing=dp(6),
                           padding=[dp(8), dp(6)])
        tools.bind(minimum_width=tools.setter('width'))
        self.tool_btns = {}
        for name, label in self.TOOLS:
            b = RoundButton(text=label, icon=name, icon_only=True, bg=DARK2,
                            fg=WHITE, size_hint_x=None, width=dp(56),
                            font_size=sp(13), radius=10)
            b.bind(on_release=lambda *_, n=name: self.set_tool(n))
            self.tool_btns[name] = b
            tools.add_widget(b)
            if name == 'text':
                ib = RoundButton(text='Image', icon='image', icon_only=True,
                                 bg=DARK2, fg=WHITE, size_hint_x=None,
                                 width=dp(56), font_size=sp(13), radius=10)
                ib.bind(on_release=lambda *_: self.pick_image())
                tools.add_widget(ib)
        tsv = ScrollView(size_hint_y=None, height=dp(56), do_scroll_y=False,
                         bar_width=0)
        tsv.add_widget(tools)
        paint_bg(tsv, BLACK)
        root.add_widget(tsv)

        self.add_widget(root)
        self.set_tool('pen')

    # ---- document state ----
    def touch_dirty(self):
        self.dirty = True
        self._title()

    def _title(self):
        name = os.path.basename(self.path) if self.path else 'Untitled.nbl'
        self.title.text = name + (' *' if self.dirty else '')

    def new_doc(self):
        self.cv.reset()
        self.path = None
        self.dirty = False
        self.set_tool('pen')
        self._title()

    def back(self):
        self.guard(lambda: setattr(App.get_running_app().sm, 'current', 'home'))

    def load(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if d.get('format') != 'nbl':
                raise ValueError('This is not a NoteBook drawing file.')
            self.cv.load_dict(d)
        except Exception as e:
            ask('Cannot open file', str(e), [('OK', None)])
            return False
        self.path = path
        self.dirty = False
        self.set_tool('pen')
        self._title()
        App.get_running_app().add_recent(path, 'nbl')
        return True

    def open_action(self):
        self.guard(lambda: FileDialog('Open drawing', 'open', ['.nbl'],
                                      self.load).open())

    def save(self, then=None):
        if self.path:
            if self._write(self.path) and then:
                then()
        else:
            self.save_as(then)

    def save_as(self, then=None):
        name = os.path.basename(self.path) if self.path else 'drawing_%s.nbl' % stamp()
        start = os.path.dirname(self.path) if self.path else None

        def cb(p):
            self.path = p
            if self._write(p) and then:
                then()
        FileDialog('Save drawing', 'save', ['.nbl'], cb, start_dir=start,
                   default_name=name).open()

    def _write(self, p):
        try:
            self.cv.select(None)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(self.cv.to_dict(), f)
        except Exception as e:
            ask('Cannot save file', str(e), [('OK', None)])
            return False
        self.dirty = False
        self._title()
        App.get_running_app().add_recent(p, 'nbl')
        toast('Saved')
        return True

    def export_png(self):
        self.cv.select(None)
        if self.path:
            out = os.path.splitext(self.path)[0] + '.png'
        else:
            out = os.path.join(storage_dir(), 'drawing_%s.png' % stamp())

        def go(dt):
            try:
                self.cv.export_to_png(out)
                toast('Exported: ' + os.path.basename(out))
            except Exception as e:
                ask('Export failed', str(e), [('OK', None)])
        Clock.schedule_once(go, .2)

    def clear_page(self):
        ask('Clear page', 'Remove everything from this page?',
            [('Clear', lambda: self.cv.clear_all(True)), ('Cancel', None)])

    def pick_bg(self):
        pick_color(self.cv.bg_color,
                   lambda c: (self.cv.set_bg(c), self.touch_dirty()))

    def open_menu(self):
        box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))
        pop = Dlg(title='Menu', content=box, size_hint=(.8, None),
                  height=min(dp(470), Window.height * .92))
        items = [('New drawing', 'new', lambda: self.guard(self.new_doc)),
                 ('Open file...', 'open', self.open_action),
                 ('Save', 'save', self.save),
                 ('Save as...', 'save_as', self.save_as),
                 ('Export PNG', 'export_png', self.export_png),
                 ('Background color', 'background', self.pick_bg),
                 ('Clear page', 'clear_page', self.clear_page),
                 ('Close', 'close', None)]

        def make(f):
            def cb(*_):
                pop.dismiss()
                if f:
                    Clock.schedule_once(lambda dt: f(), .1)
            return cb

        for t, ic, fn in items:
            b = RoundButton(text=t, icon=ic,
                            bg=DARK2 if t == 'Close' else YELLOW,
                            fg=WHITE if t == 'Close' else BLACK)
            b.bind(on_release=make(fn))
            box.add_widget(b)
        pop.open()

    # ---- tools ----
    def set_tool(self, name):
        cv = self.cv
        cv.tool = name
        cv.select(None)
        for n, b in self.tool_btns.items():
            on = n == name
            b.set_style(YELLOW if on else DARK2, BLACK if on else WHITE)
        self.refresh_props()

    def ask_text(self, x, y):
        def cb(text):
            if not text.strip():
                return
            o = TextObject(text, font_size=self.text_size,
                           color=self.cv.color, tl=(x, y))
            self.cv.add_obj(o)
            self.cv.push(('obj', o))
            self.set_tool('select')
            self.cv.select(o)
        text_prompt('Add text', '', cb, hint='Type here...')

    def pick_image(self):
        FileDialog('Choose image', 'open',
                   ['.png', '.jpg', '.jpeg', '.bmp', '.gif'],
                   self.add_image).open()

    def add_image(self, path):
        try:
            data, ext = load_image_bytes(path)
            o = ImageObject(data, ext)
        except Exception as e:
            ask('Cannot load image', str(e), [('OK', None)])
            return
        cv = self.cv
        w = min(cv.width, cv.height) * .6
        h = w * o.aspect
        if h > cv.height * .7:
            h = cv.height * .7
            w = h / o.aspect
        o.size = (w, h)
        o.center = cv.center
        cv.add_obj(o)
        cv.push(('obj', o))
        self.set_tool('select')
        cv.select(o)

    # ---- property bar ----
    def refresh_props(self):
        box = self.prop_box
        box.clear_widgets()
        cv = self.cv
        sel = cv.selected

        def btn(text, icon, fn, w=46, bg=DARK2, fg=WHITE):
            b = RoundButton(text=text, icon=icon, icon_only=True, bg=bg,
                            fg=fg, size_hint=(None, 1), width=dp(w),
                            font_size=sp(13), radius=10)
            b.bind(on_release=lambda *_: fn())
            box.add_widget(b)
            return b

        def hint(text):
            l = Label(text=text, color=GREY, size_hint=(None, 1),
                      font_size=sp(13))
            l.bind(texture_size=lambda w, ts: setattr(w, 'width', ts[0] + dp(10)))
            box.add_widget(l)

        def toggle(text, icon, attr):
            on = getattr(sel, attr)
            btn(text, icon, lambda: self._toggle(attr), w=44,
                bg=YELLOW if on else DARK2, fg=BLACK if on else WHITE)

        if isinstance(sel, TextObject):
            btn('Edit', 'edit', self._edit_text)
            btn('A-', 'font_smaller', lambda: self._scale_text(.87))
            btn('A+', 'font_larger', lambda: self._scale_text(1.15))
            toggle('B', 'bold', 'bold')
            toggle('I', 'italic', 'italic')
            toggle('U', 'underline', 'u')
            btn('Color', 'color', self._sel_color, bg=sel.color,
                fg=contrast(sel.color))
            btn('Front', 'bring_front', self._front)
            btn('Delete', 'delete', self._delete, bg=RED)
        elif isinstance(sel, ImageObject):
            btn('Smaller', 'smaller', lambda: self._scale_image(.85))
            btn('Larger', 'larger', lambda: self._scale_image(1.18))
            btn('Front', 'bring_front', self._front)
            btn('Delete', 'delete', self._delete, bg=RED)
            hint('Drag the corner square to resize')
        elif cv.tool in ('pen', 'line', 'rect', 'oval'):
            hint('Size')
            sl = Slider(min=1, max=40, value=cv.brush, size_hint=(None, 1),
                        width=dp(150), value_track=True,
                        value_track_color=YELLOW)
            lab = Label(text=str(int(cv.brush)), color=WHITE,
                        size_hint=(None, 1), width=dp(30), font_size=sp(13))

            def onv(w, v):
                cv.brush = v
                lab.text = str(int(v))
            sl.bind(value=onv)
            box.add_widget(sl)
            box.add_widget(lab)
            btn('Color', 'color', self._draw_color, bg=cv.color,
                fg=contrast(cv.color))
        elif cv.tool == 'eraser':
            hint('Drag over strokes to erase them')
        elif cv.tool == 'text':
            hint('Tap the page to add text')
            btn('A-', 'font_smaller', lambda: self._default_text(.87))
            btn('A+', 'font_larger', lambda: self._default_text(1.15))
            btn('Color', 'color', self._draw_color, bg=cv.color,
                fg=contrast(cv.color))
        else:
            hint('Tap an object to select, move or resize it')

    def _draw_color(self):
        def cb(c):
            self.cv.color = c
            self.refresh_props()
        pick_color(self.cv.color, cb)

    def _default_text(self, f):
        self.text_size = min(max(self.text_size * f, dp(10)), dp(120))
        toast('Text size: %d' % int(self.text_size / dp(1)), 0.8)

    def _mutate(self, **ch):
        o = self.cv.selected
        if isinstance(o, TextObject):
            b, a = o.mutate(**ch)
            if a != b:
                self.cv.push(('modify', o, b, a))
            self.refresh_props()

    def _scale_text(self, f):
        o = self.cv.selected
        self._mutate(font_size=min(max(o.font_size * f, dp(8)), dp(400)))

    def _toggle(self, attr):
        o = self.cv.selected
        self._mutate(**{attr: not getattr(o, attr)})

    def _edit_text(self):
        o = self.cv.selected
        text_prompt('Edit text', o.raw,
                    lambda t: t.strip() and self._mutate(raw=t))

    def _sel_color(self):
        o = self.cv.selected
        pick_color(o.color, lambda c: self._mutate(color=list(c)))

    def _scale_image(self, f):
        o = self.cv.selected
        before = o.snapshot()
        w = max(dp(30), o.width * f)
        x, top = o.x, o.top
        o.size = (w, w * o.aspect)
        o.x = x
        o.top = top
        self.cv.push(('modify', o, before, o.snapshot()))

    def _front(self):
        if self.cv.selected:
            self.cv.bring_front(self.cv.selected)

    def _delete(self):
        o = self.cv.selected
        if o:
            self.cv.push(('delobj', o))
            self.cv.remove_obj(o)


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
class NoteBookApp(App):
    title = 'NoteBook'

    def build(self):
        Window.clearcolor = WHITE
        Window.softinput_mode = 'resize'
        if platform in ('win', 'linux', 'macosx'):
            Window.size = (400, 760)
        ic = os.path.join(ICON_DIR, 'app_icon.png')
        if os.path.isfile(ic):
            self.icon = ic
        request_android_permissions()
        self.sm = ScreenManager(transition=FadeTransition(duration=.15))
        self.home = HomeScreen()
        self.notes = NotesScreen()
        self.draw = DrawScreen()
        for s in (self.home, self.notes, self.draw):
            self.sm.add_widget(s)
        Window.bind(on_keyboard=self._on_key)
        return self.sm

    def on_pause(self):
        return True

    # ---- navigation ----
    def new_notes(self):
        self.notes.new_doc()
        self.sm.current = 'notes'

    def new_drawing(self):
        self.draw.new_doc()
        self.sm.current = 'draw'

    def open_path(self, path):
        if not os.path.isfile(path):
            ask('File not found', path, [('OK', None)])
            return
        if path.lower().endswith('.nbl'):
            if self.draw.load(path):
                self.sm.current = 'draw'
        else:
            if self.notes.load(path):
                self.sm.current = 'notes'

    def _on_key(self, window, key, *args):
        if key == 27:  # Android back button / Esc
            if any(isinstance(c, ModalView) for c in Window.children):
                return True
            cur = self.sm.current
            if cur == 'notes':
                self.notes.back()
                return True
            if cur == 'draw':
                self.draw.back()
                return True
        return False

    # ---- recent files ----
    def _recent_file(self):
        return os.path.join(self.user_data_dir, 'recent.json')

    def get_recent(self):
        try:
            with open(self._recent_file(), 'r', encoding='utf-8') as f:
                items = json.load(f)
        except Exception:
            return []
        return [i for i in items if os.path.isfile(i.get('path', ''))]

    def add_recent(self, path, kind):
        items = [i for i in self.get_recent() if i['path'] != path]
        items.insert(0, {'path': path, 'kind': kind})
        try:
            with open(self._recent_file(), 'w', encoding='utf-8') as f:
                json.dump(items[:8], f)
        except Exception:
            pass


if __name__ == '__main__':
    NoteBookApp().run()