#!/usr/bin/env python3
from plumbum.cli import Application, Flag


class App(Application):
    debug = Flag(['debug', 'd'])

    def main(self):
        print(self.debug)


if __name__ == '__main__':
    print("Testing with debug=False:")
    App.invoke(debug=False)
    print("Testing with debug=True:")
    App.invoke(debug=True)
    print("Testing with no argument:")
    App.invoke()
