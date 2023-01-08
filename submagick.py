from sys import argv
import os
import argparse
import re
from functools import total_ordering


'''
parser.add_argument('integers', metavar='N', type=int, nargs='+',
                    help='an integer for the accumulator')
parser.add_argument('--sum', dest='accumulate', action='store_const',
                    const=sum, default=max,
                    help='sum the integers (default: find the max)')
'''


@total_ordering
class Timestamp():
    def __init__(self, timestamp):
        if type(timestamp) == int:
            self.timestamp = timestamp
        elif type(timestamp) == float:
            self.timestamp = int(timestamp)
        else:
            timestamp = timestamp.replace(',', '.').split('.')
            h, m, s = map(int, timestamp[0].split(':'))
            ms = int(timestamp[1].ljust(3, '0'))
            self.timestamp = 3600000 * h + 60000 * m + 1000 * s + ms
    
    def __add__(self, other):
        if type(other) == int:
            return Timestamp(self.timestamp + other)
        else:
            return Timestamp(self.timestamp + other.timestamp)
    
    def __sub__(self, other):
        if type(other) == int:
            return Timestamp(self.timestamp - other)
        else:
            return Timestamp(self.timestamp - other.timestamp)
    
    def __mul__(self, other):
        return Timestamp(int(other * self.timestamp))

    def __eq__(self, other):
        try:
            return self.timestamp == other
        except:
            return self.timestamp == other.timestamp

    def __lt__(self, other):
        try:
            return self.timestamp < other
        except:
            return self.timestamp < other.timestamp

    def __gt__(self, other):
        try:
            return self.timestamp > other
        except:
            return self.timestamp > other.timestamp

    def srt(self):
        ms, s = self.timestamp % 1000, self.timestamp // 1000
        s, m = s % 60, s // 60
        m, h = m % 60, m // 60
        return f"{h:002d}:{m:002d}:{s:002d},{ms:003d}"

    def ass(self):
        ms, s = self.timestamp % 1000, self.timestamp // 1000
        s, m = s % 60, s // 60
        m, h = m % 60, m // 60
        return f"{h:002d}:{m:002d}:{s:002d}.{ms//10:002d}"


class Dialogue():
    def __init__(self, start, end, lines, secondary=False):
        if type(start) == int or type(start) == float:
            self.start = Timestamp(start)
        else:
            self.start = start
        
        if type(end) == int or type(end) == float:
            self.end = Timestamp(end)
        else:
            self.end = end
            
        if type(lines) == str:
            self.lines = lines.split('\n')
        else:
            self.lines = list(lines)

        self.secondary = secondary

        for i in range(len(self.lines) - 1, -1, -1):
            if not self.lines[i].strip():
                self.lines.pop(i)

    def __len__(self):
        return len(self.lines)

    def ass(self):
        return "Dialogue: 0," + self.start.ass() + "," + self.end.ass() + (",Lang1" if self.secondary else ",Lang0") + ",,0,0,0,," + '\\N'.join(self.lines)
        
    def srt(self):
        return self.start.srt() + " --> " + self.end.srt() + "\n" + ("{\\an8}" if self.secondary else "") + '\n'.join(self.lines) + '\n'


def desdh(dialogues):
    dialogues_new = []
    for dialogue in dialogues:
        lines_new = []
        for line in dialogue.lines:
            line = re.sub("\（.*?\）", '', line)
            line = re.sub("\[.*?\]", '', line)
            line = re.sub("\(.*?\)", '', line)
            line = re.sub("\<.*?\>", '', line)
            line = line.replace('\u200e', '')  # never mind R2L
            line = line.lstrip('-')
            line = line.strip()
            if line:
                lines_new.append(line)
        if lines_new:
            dialogues_new.append(Dialogue(dialogue.start, dialogue.end, lines_new))
    return dialogues_new


def deass(dialogues):
    dialogues_new = []
    for dialogue in dialogues:
        lines_new = []
        
        for line in dialogue.lines:
            line = re.sub("\{.*?\}", '', line)
            line = line.lstrip('-')
            line = line.strip()
            if line:
                lines_new.append(line)
                
        if len(lines_new) == 1 and lines_new[0].startswith('m '):
            continue
            
        if lines_new:
            dialogues_new.append(Dialogue(dialogue.start, dialogue.end, lines_new))
    return dialogues_new


def lengthen(dialogues, maxduration=1., maxlines=2, keeplinebreaks=False):    
    if maxduration <= 1:
        maxlinelength = 0x10000
    else:
        maxlinelength = 0
    
    if not keeplinebreaks:
        for d0 in dialogues:
            if not d0.lines:
                print("fuck")
            maxlinelength = max(maxlinelength, max(map(len, d0.lines)))

    startTimestamps = []
    endTimestamps = []
    lineCounts = []
    dialogues_raw = []
    for d0 in dialogues:
        startTimestamps.append(d0.start.timestamp)
        if not endTimestamps:
            endTimestamps.append(maxduration * d0.end.timestamp - (maxduration - 1) * d0.start.timestamp)
        else:
            endTimestamps.append(max(endTimestamps[-1], maxduration * d0.end.timestamp - (maxduration - 1) * d0.start.timestamp))
        if sum(map(len, d0.lines)) > maxlinelength:
            lineCounts.append(len(d0.lines))
            dialogues_raw.append('\n'.join(d0.lines))
        else:
            lineCounts.append(1)
            dialogues_raw.append(' '.join(d0.lines))
    
    dialogues_new = []
    currentTimestamp = startTimestamps[0]
    i0, i1 = 0, 0
    while True:
        if i1 + 1 == len(dialogues):
            dialogues_new.append(Dialogue(
                startTimestamps[-1],
                endTimestamps[-1],
                '\n'.join(dialogues_raw[i0:])
            ))
            break
        elif endTimestamps[i1] <= startTimestamps[i1 + 1]:
            dialogues_new.append(Dialogue(
                startTimestamps[i1],
                endTimestamps[i1],
                '\n'.join(dialogues_raw[i0: i1 + 1])
            ))
            i1 += 1
            i0 = i1
        else:
            dialogues_new.append(Dialogue(
                startTimestamps[i1],
                startTimestamps[i1 + 1],
                '\n'.join(dialogues_raw[i0: i1 + 1])
            ))
            i1 += 1
            while endTimestamps[i0] <= startTimestamps[i1]:
                i0 += 1
    
    for dialogue in dialogues_new:
        dialogue.lines = dialogue.lines[-maxlines:]
    
    return dialogues_new


def compileAss(dialogues, sspos=2):
    output = ["""[Script Info]
Title: Wooh Language Learner's Subtitle
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
Aegisub Scroll Position: 129
Aegisub Active Line: 139
Aegisub Video Zoom Percent: 1.000000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lang0, Segoe UI,20,&H00FFFFFF,&H00B0B0B0,&H00000000,&HFF000000,-1,0,0,0,100,100,0.00,0.00,1,0.60,1.20, 2 ,30,10,20,0
Style: Lang1, Segoe UI,14,&H0000AAFF,&H00B0B0B0,&H00000000,&HFF000000,-1,0,0,0,75,75,0.00,0.00,1,0.45,0.90, """ + str(sspos) + """ ,30,10,8,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""]
    for dialogue in dialogues:
        output.append(dialogue.ass() + '\n')
    return ''.join(output)


def compileSrt(dialogues, sspos=2):
    output = []
    for dialogue in dialogues:
        output.append(str(len(output) + 1) + '\n' + dialogue.srt() + '\n')
    return ''.join(output)
    
    
def compile(dialogues, fmt='ass', pos=8):
    if fmt == 'ass':
        return compileAss(dialogues, sspos=pos)
    elif fmt == 'srt':
        return compileSrt(dialogues)


def readDialoguesSrt(lines):
    dialogues = []
    dialogue_raw = ""
    i = 1
    for line in lines[1:]:
        if line.strip().isdigit() and int(line) > i:
            dialogues.append(Dialogue(
                Timestamp(dialogue_raw.split('\n')[0].split("-->")[0]),
                Timestamp(dialogue_raw.split('\n')[0].split("-->")[1]),
                '\n'.join(dialogue_raw.split('\n')[1:]),
            ))
            dialogue_raw = ''
            i = int(line)
        elif line.strip():
            dialogue_raw += line
    dialogues.append(Dialogue(
        Timestamp(dialogue_raw.split('\n')[0].split("-->")[0]),
        Timestamp(dialogue_raw.split('\n')[0].split("-->")[1]),
        '\n'.join(dialogue_raw.split('\n')[1:]),
    ))
           
    return dialogues

def readDialoguesAss(lines):
    dialogues = []
    
    while not lines[0].startswith("[Events]"):
        lines.pop(0)
    while not lines[0].startswith("Format: "):
        lines.pop(0)
    
    assfmt = list(map(lambda x: x.strip(), lines[0][8:].split(',')))
    idx_start = assfmt.index("Start")
    idx_end = assfmt.index("End")
    idx_text = assfmt.index("Text")
    lines.pop(0)
    
    for line in lines:
        if not line.startswith("Dialogue: "):
            continue
        
        if "\\p" in line or '\\move' in line:
            continue
            
        text = ','.join(line.split(',')[idx_text:])
        text = text.replace('\\N', '\n')
        text = re.sub("\{.*?\}", '', text)
        
        dialogues.append(Dialogue(
            Timestamp(line.split(',')[idx_start]),
            Timestamp(line.split(',')[idx_end]),
            text,
        ))
    
    return dialogues

def readDialogues(filename, fmt=None):
    with open(filename, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        
    if fmt == None:
        fmt = filename.split('.')[-1].lower()
    
    if fmt == "srt":
        return readDialoguesSrt(lines)
    elif fmt == "ass":
        return readDialoguesAss(lines)
    else:
        raise RuntimeError("unsupported format " + fmt + " to read")
    

def improveSync(subs0, subs1):
    i, j = 0, 0
    while i < len(subs0) and j < len(subs1):
        if i == len(subs0):
            break
        elif j == len(subs1):
            break
        elif subs0[i].start <= subs1[j].start:
            if j > 0 and subs0[i].start < subs1[j - 1].start + 1000:
                if i == 0:
                    subs0[i].start = subs1[j - 1].start
                else:
                    subs0[i].start = max(subs0[i - 1].end, subs1[j - 1].start)
            if j > 0 and subs1[j - 1].end - 1000 < subs0[i].end < subs1[j - 1].end:
                if i == len(subs0) - 1:
                    subs0[i].end = subs1[j - 1].end
                else:
                    subs0[i].end = min(subs0[i + 1].start, subs1[j - 1].end)
            elif j < len(subs1) and subs1[j].end - 1000 < subs0[i].end < subs1[j].end:
                if i == len(subs0) - 1:
                    subs0[i].end = subs1[j].end
                else:
                    subs0[i].end = min(subs0[i + 1].start, subs1[j].end)
            i += 1
        else:
            if i > 0 and subs1[j].start < subs0[i - 1].start + 1000:
                if j == 0:
                    subs1[j].start = subs0[i - 1].start
                else:
                    subs1[j].start = max(subs1[j - 1].end, subs0[i - 1].start)
            if i > 0 and subs0[i - 1].end - 1000 < subs1[j].end < subs0[i - 1].end:
                if j == len(subs0) - 1:
                    subs1[j].end = subs0[i - 1].end
                else:
                    subs1[j].end = min(subs1[j + 1].start, subs0[i - 1].end)
            elif i < len(subs1) and subs0[i].end - 1000 < subs1[j].end < subs0[i].end:
                if j == len(subs0) - 1:
                    subs1[j].end = subs0[i].end
                else:
                    subs1[j].end = min(subs1[j + 1].start, subs0[i].end)
            j += 1
    return


def addSecondary(subs0, subs1, pos=2):
    if pos == 2:
        for dialogue in subs1:
            dialogue.lines = [' '.join(dialogue.lines)]
            dialogue.secondary = True
    else:
        for dialogue in subs1:
            dialogue.secondary = True

    i, j = 0, 0
    dialogues_new = []

    while i < len(subs0) and j < len(subs1):
        if i == len(subs0):
            dialogues_new += subs1[j:]
            break
        elif j == len(subs1):
            dialogues_new += subs0[i:]
            break
        elif subs0[i].start <= subs1[j].start:
            dialogues_new.append(subs0[i])
            i += 1
        else:
            dialogues_new.append(subs1[j])
            j += 1
    
    return dialogues_new
    

def main():
    parser = argparse.ArgumentParser(description='Increase subtitles display Timestamp to help language learning.')
    parser.add_argument('-i', '--input', dest='filename', help='input file name')
    parser.add_argument('-l', '--lengthen', dest='lengthen', type=float, default=1.)
    parser.add_argument('-m', '--maxlines', dest='maxlines', type=int, default=0, help='Max number of lines, applied when lengthening.')
    parser.add_argument('-s', '--sync', dest='sync', type=float, default=0.)
    parser.add_argument('-d', '--desdh', dest='desdh', action='store_true')
    parser.add_argument('-ss', '--secondsub', dest='filename1', default='', help='Secondary subtitle file name')
    parser.add_argument('-pos', '--position', dest='position', type=int, default=2, help='Secondary subtitle position in numpad notation')
    parser.add_argument('-l2', '--lengthen_second', dest='lengthen1', type=float, default=1.)
    parser.add_argument('-m2', '--maxlines_second', dest='maxlines1', type=int, default=0, help='Max number of lines, for secondary sub.')
    parser.add_argument('-s2', '--sync_second', dest='sync1', type=float, default=0.)
    parser.add_argument('-d2', '--desdh_second', dest='desdh1', action='store_true')
    parser.add_argument('--format', dest='fmt', default=None, help='output file format')
    parser.add_argument('output', help='output file name')
    parser.add_argument('-y', dest='overwrite', action='store_true', help='overwrite existing file')

    args = parser.parse_args()
    if args.fmt is None:
        args.fmt = args.output.split('.')[-1]
    
    dialogues = readDialogues(args.filename)
    if args.filename1:
        dialogues1 = readDialogues(args.filename1)
        improveSync(dialogues, dialogues1)
    else:
        dialogues1 = None
    
    if args.desdh:
        dialogues = desdh(dialogues)
    if args.desdh1:
        dialogues1 = desdh(dialogues1)
    
    if args.sync:
        for dialogue in dialogues:
            dialogue.start += int(1000 * args.sync)
            dialogue.end += int(1000 * args.sync)
    if args.sync1:
        for dialogue in dialogues1:
            dialogue.start += int(1000 * args.sync1)
            dialogue.end += int(1000 * args.sync1)
    
    if args.lengthen != 1. or args.maxlines != 0:
        if args.maxlines == 0:
            args.maxlines = 2
        dialogues = lengthen(dialogues, maxduration=args.lengthen, maxlines=args.maxlines, keeplinebreaks=False)
    if args.lengthen1 != 1. or args.maxlines1 != 0:
        if args.maxlines1 == 0:
            args.maxlines1 = 2
        dialogues1 = lengthen(dialogues1, maxduration=args.lengthen1, maxlines=args.maxlines1, keeplinebreaks=False)
    
    if dialogues1 is not None:
        dialogues = addSecondary(dialogues, dialogues1, pos=args.position)
        if args.fmt == "srt":
            print("WARNING: Secondsub formatting is nonstandard in srt. It will NOT render as expected on most players.")

    output = compile(dialogues, args.fmt, args.position)
    
    if not args.overwrite and os.path.exists(args.output):
        print("ERROR: %s exists. Use -y to overwrite" % args.output)
        exit()

    with open(args.output, "w+",encoding="utf-8") as f:
        f.write(output)
    


if __name__ == "__main__":
    main()
