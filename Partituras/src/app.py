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
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
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

SUB_PADRAO = "ou clique para escolher"
DESCRICAO = ("Anota as posições da vara do trombone acima de cada nota\n"
             "de uma partitura em PDF (clave de fá) e salva uma cópia\n"
             "\u201c<nome> - posições.pdf\u201d na mesma pasta do original.")


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

        win_w, win_h = 480, 440
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

        # ícone do app no topo
        caminho_icone = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "resources", "icon_1024.png"))
        if os.path.exists(caminho_icone):
            img = NSImage.alloc().initWithContentsOfFile_(caminho_icone)
            iv = NSImageView.imageViewWithImage_(img)
            iv.setImageScaling_(NSImageScaleProportionallyUpOrDown)
            iv.setFrame_(NSMakeRect((win_w - 96) / 2, win_h - 116, 96, 96))
            content.addSubview_(iv)

        # breve descrição do que o app faz
        desc = NSTextField.wrappingLabelWithString_(DESCRICAO)
        desc.setFont_(NSFont.systemFontOfSize_(12))
        desc.setTextColor_(NSColor.secondaryLabelColor())
        desc.setAlignment_(1)  # centro
        desc.setSelectable_(False)
        desc.setFrame_(NSMakeRect(30, win_h - 178, win_w - 60, 52))
        content.addSubview_(desc)

        # zona de soltar
        self.drop = DropView.alloc().initWithFrame_(
            NSMakeRect(20, 24, win_w - 40, win_h - 218))
        self.drop.on_files = self.receber
        content.addSubview_(self.drop)

        meio = 24 + (win_h - 218) / 2
        self.nota = _label("♪", 34, False, True)
        self.nota.setFrame_(NSMakeRect(20, meio + 14, win_w - 40, 44))
        content.addSubview_(self.nota)

        self.titulo = _label("Solte o PDF da partitura aqui", 15, True, False)
        self.titulo.setFrame_(NSMakeRect(20, meio - 16, win_w - 40, 22))
        content.addSubview_(self.titulo)

        self.sub = _label(SUB_PADRAO, 11.5, False, True)
        self.sub.setFrame_(NSMakeRect(20, meio - 38, win_w - 40, 18))
        content.addSubview_(self.sub)

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
        ok, nome, detalhe = res
        self.titulo.setStringValue_("Solte o PDF da partitura aqui")
        if ok:
            self.sub.setStringValue_(f"✓ {nome} — {detalhe}")
            self.sub.setTextColor_(NSColor.secondaryLabelColor())
        else:
            self.sub.setStringValue_(f"✕ {nome}")
            self.sub.setTextColor_(NSColor.systemRedColor())
        self.busy = False
        if not ok:
            alerta = NSAlert.alloc().init()
            alerta.setMessageText_("Não consegui anotar esta partitura")
            alerta.setInformativeText_(
                f"{nome}\n\n{detalhe}\n\n"
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
