from plumbum import cli

class MyApp(cli.Application):
    def main(self, src, dst, *eggs):
        print src, dst, eggs


if __name__ == "__main__":
    MyApp.run(["", "-h"])
