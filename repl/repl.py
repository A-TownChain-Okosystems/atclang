"""
ATCLang REPL — Interactive Shell
Version: 0.1.0-alpha | Read-Eval-Print Loop
Eigene Implementierung — kein CPython-REPL-Klon
"""

import sys, os, time, readline
sys.path.insert(0, '/app')

from atclang.compiler.compiler import compile_source, disassemble, CompileError
from atclang.vm.atcvm import ATCVM, ATCVMError


BANNER = """
╔══════════════════════════════════════════════════════╗
║          ATCLang REPL v0.1.0-alpha                   ║
║          A-TownChain Ökosystem                        ║
║                                                      ║
║  Befehle:  .help  .exit  .clear  .asm  .reset        ║
╚══════════════════════════════════════════════════════╝
"""

HELP = """
ATCLang REPL — Hilfe
──────────────────────────────────────
.help          Diese Hilfe anzeigen
.exit          REPL beenden
.clear         Bildschirm leeren
.asm           Letzten Bytecode anzeigen
.reset         VM zurücksetzen
.vars          Alle Variablen anzeigen
.events        Emittierte Events anzeigen
.gas           Gas-Verbrauch anzeigen

Beispiele:
  let x: UInt256 = 42
  let name: String = "ShivaCore"
  x + 100

ATCLang Syntax:
  wallet  contract  fn  state  emit  require
  if / elif / else  for / while  return
"""


class ATCRepl:
    def __init__(self):
        self.vm           = ATCVM()
        self.history      = []
        self.last_module  = None
        self.session_vars: dict = {}
        self._setup_readline()

    def _setup_readline(self):
        try:
            readline.set_completer(self._complete)
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass

    def _complete(self, text, state):
        keywords = [
            'wallet', 'contract', 'fn', 'state', 'emit', 'require',
            'return', 'if', 'else', 'for', 'while', 'let', 'const',
            'UInt256', 'Address', 'Bool', 'String', 'Map', 'List',
            '.help', '.exit', '.clear', '.asm', '.reset', '.vars', '.events',
        ]
        matches = [k for k in keywords if k.startswith(text)]
        return matches[state] if state < len(matches) else None

    def eval_line(self, line: str) -> str:
        """Eine Zeile ATCLang auswerten."""
        line = line.strip()
        if not line or line.startswith('//'):
            return ""

        # REPL-Befehle
        if line == '.help':   return HELP
        if line == '.exit':   raise SystemExit(0)
        if line == '.clear':  os.system('clear'); return ""
        if line == '.reset':
            self.vm.reset()
            self.vm.globals.clear()
            return "✅ VM zurückgesetzt"
        if line == '.vars':
            if not self.vm.globals:
                return "(keine Variablen)"
            return "\n".join(f"  {k} = {v!r}" for k, v in self.vm.globals.items()
                             if not k.startswith('__'))
        if line == '.events':
            evts = self.vm.get_events()
            if not evts:
                return "(keine Events)"
            return "\n".join(f"  📡 {e['event']}({', '.join(str(a) for a in e['args'])})"
                             for e in evts)
        if line == '.gas':
            return f"  Gas verbraucht: {self.vm.gas_used}"
        if line == '.asm':
            if self.last_module:
                return disassemble(self.last_module)
            return "(noch kein Code kompiliert)"

        # Ausdruck oder Statement kompilieren
        # Wenn kein Statement-Keyword → als Ausdruck mit print wrappen
        stmt_keywords = ('let', 'const', 'wallet', 'contract', 'fn',
                         'if', 'for', 'while', 'return', 'emit', 'require',
                         '//')
        is_stmt = any(line.startswith(kw) for kw in stmt_keywords)

        if is_stmt:
            source = line
        else:
            # Als Ausdruck: Ergebnis auf Stack lassen und ausgeben
            source = f"let __repl_result__ = {line}"

        try:
            module = compile_source(source)
            self.last_module = module

            # Funktionen in VM registrieren
            from atclang.vm.atcvm import ATCFunction
            for fname, instrs in module.functions.items():
                params = []
                self.vm.register_function(ATCFunction(fname, params, instrs))

            # Hauptprogramm ausführen (ohne HALT)
            instrs = [i for i in module.instructions
                      if i.op.name != 'HALT']

            result = self.vm.execute(instrs)

            # Ergebnis ausgeben
            if not is_stmt:
                val = self.vm.globals.pop('__repl_result__', result)
                if val is not None:
                    return f"  → {val!r}"
            return ""

        except CompileError as e:
            return f"  ❌ Kompilierfehler: {e}"
        except ATCVMError as e:
            return f"  ❌ VM-Fehler: {e}"
        except SyntaxError as e:
            return f"  ❌ Syntaxfehler: {e}"
        except Exception as e:
            return f"  ❌ Fehler: {type(e).__name__}: {e}"

    def run(self):
        """REPL-Hauptschleife."""
        print(BANNER)
        buf = []   # Multi-Line Buffer (für Blöcke)

        while True:
            try:
                prompt = "atc>>> " if not buf else "atc... "
                line   = input(prompt)
                self.history.append(line)

                # Multi-Line: { öffnet Block, } schließt
                buf.append(line)
                open_braces = sum(l.count('{') - l.count('}') for l in buf)

                if open_braces > 0:
                    continue   # Mehr Input warten

                full = "\n".join(buf)
                buf.clear()

                out = self.eval_line(full)
                if out:
                    print(out)

            except (EOFError, SystemExit):
                print("\n  👋 Auf Wiedersehen!")
                break
            except KeyboardInterrupt:
                buf.clear()
                print("\n  (Ctrl+C — Buffer geleert)")


# ── Direkt ausführen ─────────────────────────────────────
if __name__ == "__main__":
    repl = ATCRepl()
    repl.run()
