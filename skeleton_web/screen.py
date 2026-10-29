#!/usr/bin/env python3
"""Pty output -> the text the terminal actually showed.

A shell does not print its output in the order the bytes arrive: it redraws
what it has already drawn.  Recovering the lines that stuck is what the notes
transcript and the downloadable session log are both built on, so it lives
here on its own - pure functions over a string, no state, nothing imported
from the rest of the launcher.
"""
import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[\]P^_].*?(?:\x07|\x1b\\)|\x1b[()][A-B0-2]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Lines that are just a shell prompt being (re)drawn - dropped from the notes
# transcript, since the command itself is logged from the input side as "$ ...".
PROMPT_RE = re.compile(
    r"^(?:"
    r"[┌╭]─?─?\(.*\)-\[.*\].*"                    # kali zsh top line: ┌──(user㉿host)-[path]
    r"|[└╰]─\s?[#$%❯].*"                          # kali zsh bottom line: └─$ / └─#
    r"|[\w.\-]+@[\w.\-]+:[^\s]*\s*[#$%❯]\s*"      # user@host:path$   /   #
    r"|\([\w .\-]+\)\s*[#$%❯]\s*"                 # (venv) $
    r"|[#$%❯]\s*"                                 # a bare prompt char alone
    r")$"
)
# The same prompts with a command typed after them - the shell's own echo of the
# line it just accepted.  That echo is the only complete record of the command:
# the keystroke side never sees what zle inserted for the operator (a line
# recalled with the up-arrow, an accepted autosuggestion, a tab completion), so
# the transcript takes the command from here and keeps the typed keys only as a
# fallback for a program that does not echo at all.  Only the prompt forms that
# cannot be mistaken for output are matched: a bare "$ " or "# " starts far too
# many ordinary lines of output to be read as a prompt.
PROMPT_CMD_RE = re.compile(
    r"^(?:"
    r"[└╰]─\s?[#$%❯]"                             # kali zsh bottom line: └─$ / └─#
    r"|[\w.\-]+@[\w.\-]+:[^\s]*\s*[#$%❯]"         # user@host:path$   /   #
    r"|\([\w .\-]+\)\s*[#$%❯]"                    # (venv) $
    r")\s(?P<cmd>\S.*)$"
)
# The cursor walking backwards: a line editor repainting what it has already
# drawn.  Output does not do this - a progress bar rewrites itself with \r.
REDRAW_RE = re.compile(r"\x08|\x1b\[[0-9]*[CDG]")
# Cursor up: whatever is being drawn was drawn once already, one row higher.
# Only a repaint does that - a command line that wrapped, a prompt redrawn
# after a resize, a full-screen program.  Output moves down the page.
REPAINT_RE = re.compile(r"\x1b\[[0-9]*A")
# "cmd   cmd": a wrapped line that the repaint drew twice, both times onto the
# one row a log has (a screen would have given it two).  Long enough a match
# that "ls ls" and the like are safe.
DOUBLED_RE = re.compile(r"^(.{8,}?)\s+\1$")

def csi_num(params, default=1):
    """First numeric parameter of a CSI sequence, or `default` if it has none."""
    head = params.lstrip("?<>=").split(";")[0]
    try:
        return int(head)
    except ValueError:
        return default


# A redraw can move anywhere on the screen, so the renderer needs somewhere to
# move to; these only bound what a hostile or broken stream can make it build.
# No real screen is 200 rows tall, so no honest cursor move jumps further.
#
# The real bound on rows is the input itself - you cannot print more lines than
# you have bytes - and that is what render_screen clamps to.  _MAX_ROW is only
# the absolute ceiling above it: a flat 50000 used to cut in below a full
# scrollback of short lines, and everything past it piled onto one row, so a
# downloaded session log lost ~37000 lines of a chatty command without a word.
_MAX_COL = 4096
_MAX_ROW = 1 << 20
_MAX_JUMP = 200


def render_screen(text):
    """Pty output -> the lines the terminal ended up showing.

    Output is not the characters in the order they arrived: a shell redraws
    what it has already printed.  zsh repaints the command line it just read
    with cursor moves (ESC[nD ... ESC[nC), reprints its whole two-line prompt
    one row up (ESC[A ESC[J) every time the window is resized, and a progress
    bar overwrites itself with \r - so replaying the stream onto a cursor is
    the only way to recover the text that stuck.  Colour, titles and mode
    switches are dropped.

    A full-screen program that positions the cursor absolutely (top, an editor)
    is beyond this: it has a screen of a known height to address and a log has
    not, so ESC[H keeps the column and stays on its row.
    """
    rows = [[]]                 # the screen, as rows of characters
    r = c = 0
    i, n = 0, len(text)
    max_row = min(_MAX_ROW, n)  # one row per byte is already unreachable

    def row():
        while len(rows) <= r:
            rows.append([])
        return rows[r]

    def put(ch):
        line = row()
        if c > len(line):
            line.extend(" " * (c - len(line)))
        if c < len(line):
            line[c] = ch
        else:
            line.append(ch)

    def down(k):
        return min(r + max(k, 1), max_row)

    while i < n:
        ch = text[i]
        if ch == "\x1b":
            i += 1
            if i >= n:
                break
            kind = text[i]
            if kind == "[":                              # CSI: what moves or erases
                j = i + 1
                while j < n and not ("@" <= text[j] <= "~"):
                    j += 1
                if j >= n:
                    break
                params, final = text[i + 1:j], text[j]
                i = j + 1
                if params.startswith("?"):               # private modes: never draw
                    continue
                num = max(csi_num(params), 1)
                if final in "ABEF":                      # vertical: at most a screen
                    num = min(num, _MAX_JUMP)
                if final == "C":                         # cursor forward
                    c = min(c + num, _MAX_COL)
                elif final == "D":                       # cursor back
                    c = max(0, c - num)
                elif final == "A":                       # cursor up
                    r = max(0, r - num)
                elif final == "B":                       # cursor down
                    r = down(num)
                elif final == "E":                       # next line, column 0
                    r, c = down(num), 0
                elif final == "F":                       # previous line, column 0
                    r, c = max(0, r - num), 0
                elif final in "G`":                      # cursor to column
                    c = min(max(0, csi_num(params) - 1), _MAX_COL)
                elif final in "Hf":                      # cursor position: column only
                    parts = params.split(";")
                    col = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                    c = min(max(0, col - 1), _MAX_COL)
                elif final == "K":                       # erase in line
                    mode = csi_num(params, 0)
                    line = row()
                    if mode == 0:
                        del line[c:]
                    elif mode == 1:
                        line[:c] = [" "] * min(c, len(line))
                    else:
                        del line[:]
                elif final == "J":                       # erase in display
                    # 2 and 3 clear the screen above the cursor as well, but a
                    # log is a transcript: what scrolled past is history, and a
                    # program clearing the screen does not unsay it.
                    del row()[c:]
                    del rows[r + 1:]
                elif final == "P":                       # delete characters
                    del row()[c:c + num]
                elif final == "X":                       # erase characters
                    line = row()
                    for k in range(c, min(c + num, len(line))):
                        line[k] = " "
                elif final == "@":                       # insert blanks
                    row()[c:c] = [" "] * num
                continue
            if kind in "]P^_":                           # OSC / DCS / PM / APC: to BEL or ST
                j = i + 1
                while j < n:
                    if text[j] == "\x07":
                        break
                    if text[j] == "\x1b" and j + 1 < n and text[j + 1] == "\\":
                        j += 1
                        break
                    j += 1
                i = j + 1
                continue
            i += 1                                       # ESC = , ESC > , ESC 7 ...
            if kind in "()#%" and i < n:                 # charset select: one more byte
                i += 1
            continue
        i += 1
        if ch == "\n":
            r = down(1)
        elif ch == "\r":
            c = 0
        elif ch == "\b":
            c = max(0, c - 1)
        elif ch == "\t":
            c = min((c // 8 + 1) * 8, _MAX_COL)
        elif ch >= " " and ch != "\x7f":
            put(ch)
            c = min(c + 1, _MAX_COL)
    while len(rows) > 1 and not "".join(rows[-1]).strip():
        rows.pop()
    return "\n".join("".join(line).rstrip() for line in rows)


def flatten(text):
    """One pty line -> plain text: the last \r redraw frame, escapes stripped.

    Enough for command output, which does not redraw - a progress bar rewriting
    itself with \r is the whole of it.  A line being edited needs the renderer
    above; see _emit_notes_line."""
    if text.endswith("\r"):                           # CRLF from the pty
        text = text[:-1]
    if "\r" in text:
        text = text.split("\r")[-1]
    return ANSI_RE.sub("", text).rstrip()


def clean_output(raw):
    """Raw pty bytes -> plain text for a downloaded log: the session as the
    terminal drew it, with the escape sequences gone."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    return render_screen(text)
