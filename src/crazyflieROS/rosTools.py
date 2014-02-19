__author__ = 'ollie'
__all__= ['generateRosMessages', 'FreqMonitor','ROSNode','KBSecMonitor']
import logging
from roslib.packages import get_pkg_dir
from PyQt4.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from time import time


logger = logging.getLogger(__name__)


class ROSNode(QObject):
     def __init__(self):
         super(ROSNode, self).__init__()
         #rospy.init_node('CrazyflieDriver')


def generateRosMessages(toc):
    """ Generates the *.msg files for ROS from the TOC
    """
    if not toc:
        logger.warn("No TOC available to generate ROS messages from")
        return

    path = get_pkg_dir('crazyflieROS')+"/msg/"
    for g in toc.keys():
        makeMsg(g, path, toc[g] )


def makeMsg(name, path, members):
    file = open(path+name+".msg", 'w')
    file.write("Header header\n")
    for m in sorted(members.keys()):
        # type, remove the _t or append 32
        t = members[m].ctype[:-2] if members[m].ctype!="float" else members[m].ctype+"32"
        file.write("%s %s\n" % (t, members[m].name))
    file.close()

class FreqMonitor():
    """
    Modified from ros_comm / tools / rostopic / src / rostopic / __init__.py
    ROSTopicHz receives messages for a topic and computes frequency stats
    """
    def __init__(self,window=200):
        self.last_printed_tn = 0
        self.msg_t0 = -1.
        self.msg_tn = 0
        self.times =[]
        self.window_size = window
        self.last_rate = 0


    def count(self):
        # curr_rostime = rospy.get_rostime()
        # # time reset
        # if curr_rostime.is_zero():
        #     if len(self.times) > 0:
        #         # print("time has reset, resetting counters")
        #         self.times = []
        #     return
        curr = time()
        if self.msg_t0 < 0 or self.msg_t0 > curr:
            self.msg_t0 = curr
            self.msg_tn = curr
            self.times = []
        else:
            self.times.append(curr - self.msg_tn)
            self.msg_tn = curr

        #only keep statistics for the last X messages so as not to run out of memory
        if len(self.times) > self.window_size - 1:
            self.times.pop(0)

    def get_hz(self,use_cached = False):
        if use_cached:
            return self.last_rate
        if not self.times:
            rate = 0
        elif self.msg_tn == self.last_printed_tn:
            rate = 0
        else:
            n = len(self.times)
            #rate = (n - 1) / (rospy.get_time() - self.msg_t0)
            mean = sum(self.times) / n
            rate = 1./mean if mean > 0. else 0
            self.last_printed_tn = self.msg_tn
        self.last_rate = rate
        return rate




from bisect import bisect_left
class KBSecMonitor(QObject):
    """
    Reports kb per second at X hz
    """
    sig_KBPS = pyqtSignal(int)

    def __init__(self):
        super(KBSecMonitor, self).__init__()
        self.times = []
        self.amounts = []
        self.sum = 0 # Quicker to keep a running sum
        self.timer = QTimer()
        self.hz = 0
        self.timer.timeout.connect(self.getKBPS)
        self.falseStopped = False # If we stop cause hz was set to 0, be able to resume


    @pyqtSlot(int)
    def setHZ(self, hz):
        if hz <= 0:
            self.stop()
            self.falseStopped = True
        else:
            self.timer.setInterval(1000/hz)
            if self.falseStopped:
                self.start()
        self.hz = hz

    @pyqtSlot()
    def stop(self):
        self.timer.stop()
        self.clear()
        self.falseStopped = False
        self.sig_KBPS.emit(0)

    @pyqtSlot()
    def start(self):
        if self.hz>0:
            self.timer.start()
        else:
            self.falseStopped = True

    @pyqtSlot(int)
    def count(self, kb):
        self.times.append(time())
        self.amounts.append(kb)
        self.sum += kb

    @pyqtSlot(int, result=int)
    def getKBPS(self):
        i = bisect_left( self.times , time()-1)
        self.sum -= sum(self.amounts[0:i])
        self.times = self.times[i:]
        self.amounts = self.amounts[i:]
        self.sig_KBPS.emit(self.sum)
        return sum

    @pyqtSlot()
    def clear(self):
        self.times = []
        self.amounts = []
        self.sum = 0 # Quicker to keep a running sum


