from plumbum import cli, colors

class SimpleApp(cli.Application):
    PROGNAME = colors.green
    VERSION = colors.red | "1.0.3"

    @cli.switch(["a"])
    def spam(self):
        print("!!a")

    def main(self, *args):
        print("lalala")


class TestSimpleApp(object):
    def test_runs(self):
        _, rc = SimpleApp.run(['SimpleApp'], exit = False)
        assert rc == 0

    def test_colorless_run(self, capsys):
        colors.use_color = 0
        _, rc = SimpleApp.run(["SimpleApp"], exit = False)
        assert capsys.readouterr()[0]  == 'lalala\n'


        colors.use_color = 4
        _, rc = SimpleApp.run(["SimpleApp"], exit = False)
        assert capsys.readouterr()[0]  == 'lalala\n'


    def test_colorless_output(self, capsys):
        colors.use_color = 0
        _, rc = SimpleApp.run(["SimpleApp", "-h"], exit = False)
        output = capsys.readouterr()[0]
        assert 'SimpleApp 1.0.3' in output
        assert 'SimpleApp [SWITCHES] args...' in output

    def test_colorful_help(self, capsys):
        colors.use_color = 4
        _, rc = SimpleApp.run(["SimpleApp", "-h"], exit = False)
        output = capsys.readouterr()[0]
        assert 'SimpleApp 1.0.3' not in output
        assert SimpleApp.PROGNAME | 'SimpleApp' in output





class TestNSApp(object):

    def test_colorful_output(self, capsys):
        colors.use_color = 4
        class NotSoSimpleApp(cli.Application):
            PROGNAME = colors.blue | "NSApp"
            VERSION = "1.2.3"
            COLOR_GROUPS = {'Switches': colors.green}

            @cli.switch(["b"], help="this is a bacon switch")
            def bacon(self):
                print("Oooooh, I love BACON!")

            @cli.switch(["c"], help=colors.red | "crunchy")
            def crunchy(self):
                print("Crunchy...")

            def main(self):
                print("Eating!")

        _, rc = NotSoSimpleApp.run(["NotSoSimpleApp", "-h"], exit=False)
        output = capsys.readouterr()[0]
        assert rc == 0
        expected = str((colors.blue | "NSApp") + " 1.2.3") 
        assert "-b" in output
        assert str(colors.red | "crunchy") in output
        assert expected in output

if __name__ == "__main__":
    NotSoSimpleApp.run()
