from plumbum import cli

class MyApp(cli.Application):
    PROGNAME = "Foobar"
    VERSION = "7.3"

if __name__ == "__main__":
    MyApp.run(["", "-h"])
