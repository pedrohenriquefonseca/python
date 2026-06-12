"""App de Mac do Partituras — janela minimalista de soltar e pronto.

Solte um PDF de partitura (ou clique para escolher): o app escreve as
posições de vara acima das notas e salva "<nome original> - posições.pdf"
na mesma pasta do arquivo solto.
"""

from __future__ import annotations

import os
import threading
import traceback

import objc
from AppKit import (
    NSAlert,
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSDragOperationCopy,
    NSDragOperationNone,
    NSFont,
    NSImage,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSOpenPanel,
    NSPasteboardURLReadingFileURLsOnlyKey,
    NSScreen,
    NSTextField,
    NSURL,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskTitled,
)
from PyObjCTools import AppHelper

from annotate import annotate

MAX_RECENTES = 6


def _label(text: str, size: float, bold: bool, gray: bool) -> NSTextField:
    lb = NSTextField.labelWithString_(text)
    weight = NSFont.boldSystemFontOfSize_ if bold else NSFont.systemFontOfSize_
    lb.setFont_(weight(size))
    if gray:
        lb.setTextColor_(NSColor.secondaryLabelColor())
    lb.setAlignment_(1)  # centro
    return lb


class DropView(NSView):
    """Zona de soltar com borda tracejada; clique abre o seletor."""

    def initWithFrame_(self, frame):
        self = objc.super(DropView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.registerForDraggedTypes_(["public.file-url"])
        self.highlight = False
        self.on_files = None
        return self

    def drawRect_(self, rect):
        bounds = self.bounds()
        box = NSMakeRect(bounds.origin.x + 4, bounds.origin.y + 4,
                         bounds.size.width - 8, bounds.size.height - 8)
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(box, 12, 12)
        path.setLineWidth_(2 if self.highlight else 1.5)
        path.setLineDash_count_phase_([6.0, 4.0], 2, 0.0)
        color = (NSColor.controlAccentColor() if self.highlight
                 else NSColor.tertiaryLabelColor())
        color.set()
        path.stroke()

    @objc.python_method
    def _urls(self, sender):
        pb = sender.draggingPasteboard()
        urls = pb.readObjectsForClasses_options_(
            [NSURL], {NSPasteboardURLReadingFileURLsOnlyKey: True}) or []
        return [u.path() for u in urls if u.path().lower().endswith(".pdf")]

    def draggingEntered_(self, sender):
        if self._urls(sender):
            self.highlight = True
            self.setNeedsDisplay_(True)
            return NSDragOperationCopy
        return NSDragOperationNone

    def draggingExited_(self, sender):
        self.highlight = False
        self.setNeedsDisplay_(True)

    def performDragOperation_(self, sender):
        self.highlight = False
        self.setNeedsDisplay_(True)
        paths = self._urls(sender)
        if paths and self.on_files:
            self.on_files(paths)
        return bool(paths)

    def mouseDown_(self, event):
        panel = NSOpenPanel.openPanel()
        panel.setAllowedFileTypes_(["pdf"])
        panel.setAllowsMultipleSelection_(True)
        if panel.runModal() and self.on_files:
            paths = [u.path() for u in panel.URLs()]
            if paths:
                self.on_files(paths)


class App:
    def __init__(self):
        self.busy = False
        self.fila: list[str] = []
        self.recentes: list[tuple[bool, str, str]] = []  # (ok, nome, detalhe)

        win_w, win_h = 480, 430
        screen = NSScreen.mainScreen().frame()
        rect = NSMakeRect((screen.size.width - win_w) / 2,
                          (screen.size.height - win_h) / 2, win_w, win_h)
        style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                 | NSWindowStyleMaskMiniaturizable)
        self.win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False)
        self.win.setTitle_("Partituras")
        self.win.setReleasedWhenClosed_(False)
        content = self.win.contentView()

        self.drop = DropView.alloc().initWithFrame_(
            NSMakeRect(20, win_h - 240, win_w - 40, 220))
        self.drop.on_files = self.receber
        content.addSubview_(self.drop)

        self.icone = _label("♪", 36, False, True)
        self.icone.setFrame_(NSMakeRect(20, win_h - 130, win_w - 40, 48))
        content.addSubview_(self.icone)

        self.titulo = _label("Solte o PDF da partitura aqui", 15, True, False)
        self.titulo.setFrame_(NSMakeRect(20, win_h - 165, win_w - 40, 22))
        content.addSubview_(self.titulo)

        self.sub = _label("ou clique para escolher — salva “<nome> - posições.pdf” na mesma pasta",
                          11.5, False, True)
        self.sub.setFrame_(NSMakeRect(20, win_h - 188, win_w - 40, 18))
        content.addSubview_(self.sub)

        self.linhas: list[tuple[NSTextField, NSTextField]] = []
        y = win_h - 280
        for _ in range(MAX_RECENTES):
            esq = NSTextField.labelWithString_("")
            esq.setFont_(NSFont.systemFontOfSize_(12))
            esq.setFrame_(NSMakeRect(28, y, win_w - 180, 17))
            esq.setLineBreakMode_(5)  # truncar no meio
            content.addSubview_(esq)
            dirt = NSTextField.labelWithString_("")
            dirt.setFont_(NSFont.systemFontOfSize_(12))
            dirt.setTextColor_(NSColor.secondaryLabelColor())
            dirt.setAlignment_(2)  # direita
            dirt.setFrame_(NSMakeRect(win_w - 160, y, 132, 17))
            content.addSubview_(dirt)
            self.linhas.append((esq, dirt))
            y -= 24

        self.win.makeKeyAndOrderFront_(None)

    # ---------- fluxo ----------

    def receber(self, paths: list[str]):
        self.fila.extend(paths)
        self.processar()

    def processar(self):
        if self.busy or not self.fila:
            return
        caminho = self.fila.pop(0)
        self.busy = True
        nome = os.path.basename(caminho)
        self.titulo.setStringValue_(f"Anotando {nome}…")
        threading.Thread(target=self._trabalho, args=(caminho,), daemon=True).start()

    def _trabalho(self, caminho: str):
        nome = os.path.basename(caminho)
        stem, _ = os.path.splitext(nome)
        saida = os.path.join(os.path.dirname(caminho), f"{stem} - posições.pdf")
        try:
            n, fonte = annotate(caminho, saida)
            res = (True, os.path.basename(saida), f"{n} posições · {fonte:g}pt")
        except Exception as e:
            traceback.print_exc()
            res = (False, nome, str(e)[:60])
        AppHelper.callAfter(self._terminou, res)

    def _terminou(self, res):
        self.recentes.insert(0, res)
        del self.recentes[MAX_RECENTES:]
        for (esq, dirt), item in zip(self.linhas, self.recentes + [None] * MAX_RECENTES):
            if item is None:
                esq.setStringValue_("")
                dirt.setStringValue_("")
                continue
            ok, nome, detalhe = item
            esq.setStringValue_(("✓ " if ok else "✕ ") + nome)
            esq.setTextColor_(NSColor.labelColor() if ok
                              else NSColor.systemRedColor())
            dirt.setStringValue_(detalhe)
        self.titulo.setStringValue_("Solte o PDF da partitura aqui")
        self.busy = False
        if not self.recentes[0][0]:
            alerta = NSAlert.alloc().init()
            alerta.setMessageText_("Não consegui anotar esta partitura")
            alerta.setInformativeText_(
                f"{self.recentes[0][1]}\n\n{self.recentes[0][2]}\n\n"
                "Confira se é um PDF vetorial exportado do MuseScore "
                "(não escaneado).")
            alerta.runModal()
        self.processar()


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # ícone do Dock: como o processo é o python3 (wrapper), o ícone do
    # bundle não é herdado — carrega o master do repositório.
    icone = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "resources", "icon_1024.png"))
    if os.path.exists(icone):
        img = NSImage.alloc().initWithContentsOfFile_(icone)
        if img:
            app.setApplicationIconImage_(img)

    menubar = NSMenu.alloc().init()
    app_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_("Encerrar Partituras",
                                                    "terminate:", "q")
    app_item.setSubmenu_(app_menu)
    app.setMainMenu_(menubar)

    App()
    app.activateIgnoringOtherApps_(True)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
