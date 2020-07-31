import sys
import time
import signalslot

class Progressbar():
    def __init__(self, size, prefix):
        self.size = size
        self.prefix = prefix
        self.count = 1
        self.file = sys.stdout
        self.signal = signalslot.Signal(args=['index'])
        self.signal.connect(self.show)
        self.index = 0

    def show(self, index, **kwargs):
        index += 1
        x = int(self.size*index/self.count)
        self.file.write("%s[%s%s] %i/%i   \r" % (self.prefix,
                                                 "#"*x, "."*(self.size-x),
                                                 index, self.count))
        self.file.flush()

        if index != self.count:
            return

        self.file.write("\n")
        self.file.flush()

    def emit(self, index):
        self.signal.emit(index=index)

    def emit_increment(self):
        self.signal.emit(index=self.index)
        self.index += 1
        if self.count == self.index:
            self.index = 0
