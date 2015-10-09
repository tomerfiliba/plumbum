import plumbum
#from plumbum.colorlib import HTMLStyle, StyleFactory
#plumbum.colors = StyleFactory(HTMLStyle)

from plumbum import cli, colors

class MyApp(cli.Application):
    PROGNAME = colors.green
    VERSION = colors.blue | "1.0.2"
    COLOR_GROUPS = {"Meta-switches" : colors.bold & colors.yellow}
    opts =  cli.Flag("--ops", help=colors.magenta | "This is help")
    
    def main(self):
        print("HI")

if __name__ == "__main__":
    MyApp.run()
