#!/usr/bin/env python3

import ast
import math
import operator
import re

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib


APP_NAME = "Nexora Calc"
VERSION = "1.0.0"


# ------------------------------------------------------------
# Safe expression evaluator
# ------------------------------------------------------------

class SafeCalculator:
    BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.FloorDiv: operator.floordiv,
    }

    UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    FUNCTIONS = {
        "sin": lambda x: math.sin(math.radians(x)),
        "cos": lambda x: math.cos(math.radians(x)),
        "tan": lambda x: math.tan(math.radians(x)),
        "asin": lambda x: math.degrees(math.asin(x)),
        "acos": lambda x: math.degrees(math.acos(x)),
        "atan": lambda x: math.degrees(math.atan(x)),
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    @classmethod
    def evaluate(cls, expression):
        expression = expression.strip()

        if not expression:
            raise ValueError("Empty expression")

        expression = expression.replace("×", "*")
        expression = expression.replace("÷", "/")
        expression = expression.replace("−", "-")
        expression = expression.replace("^", "**")

        expression = re.sub(
            r"(\d+(?:\.\d+)?)%",
            r"(\1/100)",
            expression
        )

        tree = ast.parse(expression, mode="eval")
        result = cls._eval(tree.body)

        if not math.isfinite(result):
            raise ValueError("Invalid result")

        return result

    @classmethod
    def _eval(cls, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Invalid constant")

        if isinstance(node, ast.BinOp):
            operation = cls.BIN_OPS.get(type(node.op))
            if operation is None:
                raise ValueError("Operation not allowed")

            left = cls._eval(node.left)
            right = cls._eval(node.right)

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            operation = cls.UNARY_OPS.get(type(node.op))
            if operation is None:
                raise ValueError("Unary operation not allowed")

            return operation(cls._eval(node.operand))

        if isinstance(node, ast.Name):
            if node.id in cls.CONSTANTS:
                return cls.CONSTANTS[node.id]

            raise ValueError("Unknown constant")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Invalid function")

            function = cls.FUNCTIONS.get(node.func.id)

            if function is None:
                raise ValueError("Unknown function")

            if len(node.args) != 1:
                raise ValueError("Function requires one argument")

            return function(cls._eval(node.args[0]))

        raise ValueError("Expression not allowed")


# ------------------------------------------------------------
# Main application
# ------------------------------------------------------------

class NexoraCalc(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id="com.nexora.NexoraCalc"
        )

        self.expression = ""
        self.memory = 0.0
        self.history = []
        self.scientific = False
        self.dark_mode = True

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(
            application=self,
            title=APP_NAME,
            default_width=430,
            default_height=680
        )

        self.build_ui()
        self.window.present()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):
        self.apply_css()

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0
        )

        # Header
        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )
        header.set_margin_top(14)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_bottom(10)

        title = Gtk.Label(label="Nexora Calc")
        title.add_css_class("app-title")

        subtitle = Gtk.Label(label="NEXORA")
        subtitle.add_css_class("brand")

        header.append(title)
        header.append(subtitle)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        sci_button = Gtk.Button(label="SCI")
        sci_button.add_css_class("header-button")
        sci_button.connect("clicked", self.toggle_scientific)
        header.append(sci_button)

        theme_button = Gtk.Button(label="☾")
        theme_button.add_css_class("header-button")
        theme_button.connect("clicked", self.toggle_theme)
        header.append(theme_button)

        root.append(header)

        # Display
        display_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )
        display_box.set_margin_start(16)
        display_box.set_margin_end(16)
        display_box.set_margin_top(12)
        display_box.set_margin_bottom(16)

        self.display = Gtk.Entry()
        self.display.set_text("")
        self.display.set_alignment(1.0)
        self.display.set_placeholder_text("0")
        self.display.add_css_class("display")
        self.display.connect("activate", self.calculate)

        display_box.append(self.display)

        self.status = Gtk.Label(label="Ready")
        self.status.set_xalign(1)
        self.status.add_css_class("status")
        display_box.append(self.status)

        root.append(display_box)

        # Memory row
        memory = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )
        memory.set_margin_start(16)
        memory.set_margin_end(16)
        memory.set_margin_bottom(8)

        for text, callback in [
            ("MC", self.memory_clear),
            ("MR", self.memory_recall),
            ("M+", self.memory_add),
            ("M−", self.memory_subtract),
        ]:
            button = Gtk.Button(label=text)
            button.add_css_class("memory-button")
            button.connect("clicked", callback)
            memory.append(button)

        root.append(memory)

        # Main keypad
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(7)
        self.grid.set_column_spacing(7)
        self.grid.set_margin_start(16)
        self.grid.set_margin_end(16)
        self.grid.set_margin_bottom(16)

        buttons = [
            ["C", "⌫", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["±", "0", ".", "="],
        ]

        for row, values in enumerate(buttons):
            for col, value in enumerate(values):
                button = Gtk.Button(label=value)
                button.set_hexpand(True)
                button.set_vexpand(True)

                if value in ["÷", "×", "−", "+", "="]:
                    button.add_css_class("operator-button")
                elif value in ["C", "⌫", "%"]:
                    button.add_css_class("function-button")
                else:
                    button.add_css_class("number-button")

                button.connect("clicked", self.button_clicked, value)

                self.grid.attach(button, col, row, 1, 1)

        root.append(self.grid)

        # Scientific keypad
        self.scientific_grid = Gtk.Grid()
        self.scientific_grid.set_row_spacing(7)
        self.scientific_grid.set_column_spacing(7)
        self.scientific_grid.set_margin_start(16)
        self.scientific_grid.set_margin_end(16)
        self.scientific_grid.set_margin_bottom(12)
        self.scientific_grid.set_visible(False)

        scientific_buttons = [
            ["sin", "cos", "tan", "sqrt"],
            ["asin", "acos", "atan", "log"],
            ["ln", "abs", "floor", "ceil"],
            ["π", "e", "(", ")"],
        ]

        for row, values in enumerate(scientific_buttons):
            for col, value in enumerate(values):
                button = Gtk.Button(label=value)
                button.set_hexpand(True)
                button.add_css_class("scientific-button")
                button.connect("clicked", self.button_clicked, value)
                self.scientific_grid.attach(button, col, row, 1, 1)

        root.append(self.scientific_grid)

        # Bottom row
        bottom = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )
        bottom.set_margin_start(16)
        bottom.set_margin_end(16)
        bottom.set_margin_bottom(12)

        history_button = Gtk.Button(label="History")
        history_button.add_css_class("bottom-button")
        history_button.connect("clicked", self.show_history)

        copy_button = Gtk.Button(label="Copy")
        copy_button.add_css_class("bottom-button")
        copy_button.connect("clicked", self.copy_result)

        clear_history = Gtk.Button(label="Clear History")
        clear_history.add_css_class("bottom-button")
        clear_history.connect("clicked", self.clear_history)

        bottom.append(history_button)
        bottom.append(copy_button)
        bottom.append(clear_history)

        root.append(bottom)

        footer = Gtk.Label(
            label=f"Nexora Software • v{VERSION}"
        )
        footer.add_css_class("footer")
        footer.set_margin_bottom(10)

        root.append(footer)

        self.window.set_child(root)

        # Keyboard shortcuts
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self.on_key_pressed)
        self.window.add_controller(controller)

    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    def button_clicked(self, button, value):
        if value == "C":
            self.clear()
            return

        if value == "⌫":
            self.expression = self.expression[:-1]
            self.display.set_text(self.expression)
            return

        if value == "=":
            self.calculate()
            return

        if value == "±":
            if self.expression.startswith("-"):
                self.expression = self.expression[1:]
            else:
                self.expression = "-" + self.expression

        elif value == "π":
            self.expression += "pi"

        elif value == "e":
            self.expression += "e"

        elif value in [
            "sin", "cos", "tan",
            "asin", "acos", "atan",
            "sqrt", "log", "ln",
            "abs", "floor", "ceil"
        ]:
            self.expression += f"{value}("

        else:
            self.expression += value

        self.display.set_text(self.expression)
        self.status.set_text("Typing…")

    def clear(self):
        self.expression = ""
        self.display.set_text("")
        self.status.set_text("Ready")

    # --------------------------------------------------------
    # Calculate
    # --------------------------------------------------------

    def calculate(self, *args):
        try:
            expression = self.expression

            if not expression:
                return

            result = SafeCalculator.evaluate(expression)

            formatted = self.format_number(result)

            self.history.insert(
                0,
                f"{expression} = {formatted}"
            )

            self.history = self.history[:50]

            self.expression = formatted
            self.display.set_text(formatted)
            self.status.set_text("Calculated")

        except ZeroDivisionError:
            self.status.set_text("Cannot divide by zero")

        except Exception:
            self.status.set_text("Invalid expression")

    @staticmethod
    def format_number(number):
        if number == int(number):
            return str(int(number))

        return f"{number:.12g}"

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    def get_current_value(self):
        try:
            return SafeCalculator.evaluate(
                self.display.get_text()
            )
        except Exception:
            return 0.0

    def memory_clear(self, button):
        self.memory = 0.0
        self.status.set_text("Memory cleared")

    def memory_recall(self, button):
        self.expression = self.format_number(self.memory)
        self.display.set_text(self.expression)
        self.status.set_text("Memory recalled")

    def memory_add(self, button):
        self.memory += self.get_current_value()
        self.status.set_text("Added to memory")

    def memory_subtract(self, button):
        self.memory -= self.get_current_value()
        self.status.set_text("Subtracted from memory")

    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    def show_history(self, button):
        dialog = Gtk.Dialog(
            title="Calculation History",
            transient_for=self.window,
            modal=True
        )

        dialog.set_default_size(400, 450)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )

        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        if not self.history:
            label = Gtk.Label(label="No calculations yet.")
            content.append(label)
        else:
            for item in self.history:
                label = Gtk.Label(label=item)
                label.set_xalign(0)
                label.set_wrap(True)
                content.append(label)

        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: dialog.close())

        content.append(close)

        dialog.set_child(content)
        dialog.present()

    def clear_history(self, button):
        self.history.clear()
        self.status.set_text("History cleared")

    # --------------------------------------------------------
    # Clipboard
    # --------------------------------------------------------

    def copy_result(self, button):
        text = self.display.get_text()

        if not text:
            return

        clipboard = self.window.get_clipboard()
        clipboard.set(text)

        self.status.set_text("Copied to clipboard")

    # --------------------------------------------------------
    # Scientific mode
    # --------------------------------------------------------

    def toggle_scientific(self, button):
        self.scientific = not self.scientific
        self.scientific_grid.set_visible(self.scientific)

        if self.scientific:
            self.window.set_default_size(430, 850)
        else:
            self.window.set_default_size(430, 680)

    # --------------------------------------------------------
    # Theme
    # --------------------------------------------------------

    def toggle_theme(self, button):
        self.dark_mode = not self.dark_mode

        display = Gdk.Display.get_default()
        settings = Gtk.Settings.get_default()

        if self.dark_mode:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        else:
            settings.set_property("gtk-application-prefer-dark-theme", False)

    # --------------------------------------------------------
    # Keyboard
    # --------------------------------------------------------

    def on_key_pressed(self, controller, keyval, keycode, state):
        key = Gdk.keyval_name(keyval)

        if key in ("Return", "KP_Enter"):
            self.calculate()
            return True

        if key == "Escape":
            self.clear()
            return True

        if key == "BackSpace":
            self.expression = self.expression[:-1]
            self.display.set_text(self.expression)
            return True

        if key in "0123456789.+-*/()%":
            char = key

            if char == "*":
                char = "×"

            elif char == "/":
                char = "÷"

            elif char == "-":
                char = "−"

            self.expression += char
            self.display.set_text(self.expression)
            return True

        return False

    # --------------------------------------------------------
    # CSS
    # --------------------------------------------------------

    def apply_css(self):
        css = b"""
        window {
            background: #0b0f19;
        }

        .app-title {
            font-size: 25px;
            font-weight: 800;
            color: #f5f7ff;
        }

        .brand {
            font-size: 10px;
            font-weight: 700;
            color: #6c63ff;
            margin-left: 6px;
        }

        .display {
            min-height: 80px;
            font-size: 38px;
            font-weight: 600;
            color: #ffffff;
            background: #111827;
            border-radius: 18px;
            padding: 12px 18px;
            border: 1px solid #252d3d;
        }

        .status {
            color: #8b95aa;
            font-size: 12px;
            margin-top: 4px;
        }

        button {
            border-radius: 14px;
            min-height: 55px;
            font-size: 19px;
            font-weight: 600;
            border: none;
        }

        .number-button {
            background: #182131;
            color: #ffffff;
        }

        .number-button:hover {
            background: #222d40;
        }

        .operator-button {
            background: #6c63ff;
            color: white;
        }

        .operator-button:hover {
            background: #7c74ff;
        }

        .function-button {
            background: #273247;
            color: #d9deea;
        }

        .scientific-button {
            background: #172033;
            color: #aeb8ff;
            min-height: 48px;
        }

        .memory-button {
            background: #121a29;
            color: #929db3;
            min-height: 40px;
            font-size: 13px;
        }

        .header-button {
            background: #172033;
            color: #b9c1ff;
            min-height: 38px;
            min-width: 48px;
            font-size: 12px;
        }

        .bottom-button {
            background: #141d2c;
            color: #9da8bd;
            min-height: 38px;
            font-size: 12px;
        }

        .footer {
            color: #505a6c;
            font-size: 10px;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def main():
    app = NexoraCalc()
    return app.run()


if __name__ == "__main__":
    main()
