#!/usr/bin/python
from gerber2pdf import *
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import csv
import Tkinter, tkFileDialog
root = Tkinter.Tk()
root.withdraw()
dirname = tkFileDialog.askdirectory(parent=root,initialdir="/",title='Please select directory where Gerber and Pick and Place(CSV) files are located all files should be in the same folder')


class PPComponent:
    def __init__(self,xc, yc, w, h, name, desc, ref):
        self.xc = xc
        self.yc = yc
        self.w = w
        self.h = h
        if(self.w == 0):
            self.w = 0.8 * mm

        if(self.h == 0):
            self.h = 0.8 * mm

        self.name = name
        self.desc = desc
        self.ref = ref

class PickAndPlaceFile:
    def split_parts(self, layer, index, n_comps):
        parts = []
        n=0
        for i in sorted(self.layers[layer].iterkeys()):
            if(n >= index and n < index+n_comps):
                parts.append(self.layers[layer][i])
            n=n+1
        return parts

    def num_groups(self, layer):
        return len(self.split_parts(layer, 0, 10000))

    def draw(self, layer, index, n_comps, canv):
        parts = self.split_parts(layer, index, n_comps)
        n=0
        for i in parts:
            canv.setStrokeColor(self.col_map[n])
            canv.setFillColor(self.col_map[n])
            n=n+1
            for j in i:
                canv.rect(j.xc - j.w/2, j.yc-j.h/2, j.w, j.h, 1, 1)

    def gen_table(self, layer, index, n_comps,canv):
        parts = self.split_parts(layer, index, n_comps)

        yt = 260 * mm
        canv.setFont("Helvetica",10)
        canv.setStrokeGray(0)
        canv.setFillGray(0)
        canv.drawString(20 * mm, yt, "Color")
        canv.drawString(40 * mm, yt, "Package")
        canv.drawString(80 * mm, yt, "Value")
        canv.drawString(120 * mm, yt, "Designators")
        n=0
        for group in parts:
            dsgn = ""
            yt = yt - 6 * mm
            canv.setFillColor(self.col_map[n])
            canv.rect(20 *mm, yt, 10 * mm, 3 * mm, 1, 1)
            canv.setFillGray(0)
            n=n+1
            for part in group:
                dsgn = dsgn + " " + part.name
            canv.drawString(120 * mm, yt, dsgn)
            canv.drawString(40 * mm, yt, group[0].ref[0:20])
            canv.drawString(80 * mm, yt, group[0].desc[0:20])


class PickAndPlaceFileKicad(PickAndPlaceFile):
    def __init__(self, fname):
        print("Load pick and place file")
        with open(fname, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',',)
            rows = []
            for row in reader:
                rows.append(row)

            self.col_map = [colors.Color(1,0,0), colors.Color(1,1,0), colors.Color(0,1,0), colors.Color(0,1,1), colors.Color(1,0,1), colors.Color(0,0,1)]

            i_ref = rows[0].index("Designator")
            i_val = rows[0].index("Comment")
            i_package = rows[0].index("Footprint")
            i_cx = rows[0].index("Ref X")
            i_cy = rows[0].index("Ref Y")
            i_rot = rows[0].index("Rotation")
            i_layer = rows[0].index("Layer")

            self.layers = {"T":{}, "B":{}}

            for i in rows[2:]:
                if(len(i)>0):
                    cxi= str(i[i_cx]);
                    cxi = cxi.replace("mm","")
                    cyi= str(i[i_cy]);
                    cyi = cyi.replace("mm","")
                    cx = float(cxi) * mm
                    cy = float(cyi) * mm
                    layer = i[i_layer]
                    ref = i[i_val]
                    if(ref not in self.layers[layer]):
                        self.layers[layer][ref] = []
                    self.layers[layer][ref].append(PPComponent(cx, cy, 1*mm, 1*mm, i[i_ref], ref, i[i_package]))
                    #print([cx, cy, 1*mm, 1*mm, ref, i[i_val], i[i_package]])
                    #self.layers[layer][ref].append(PPComponent(cx, cy, 1 * mm, 1 * mm, ref, i[i_val], i[i_package]))


def findFileInDir(dir_path, file_extension):
    for file in os.listdir(dir_path):
        if file.endswith(file_extension):
            print(file_extension+" file found:"+os.path.join(dir_path, file))
            return os.path.join(dir_path, file)
    raise Exception('{0} file not found in {1} directory!'.format(file_extension, dir_path))

def renderGerber(path, layer, canv):
    global gerberExtents
    if(layer == "bottom"):
        f_copper = findFileInDir(path, ".GBL")
        f_overlay = findFileInDir(path, ".GBO")
    else:
        f_copper = findFileInDir(path, ".GTL")
        f_overlay = findFileInDir(path, ".GTO")

    canv.setLineWidth(0.0)
    gm = GerberMachine( "", canv )
    gm.Initialize()
    ResetExtents()
    gm.setColors(colors.Color(0.85,0.85,0.85), colors.Color(0,0,0))
    gm.ProcessFile(f_copper)
    gm.setColors(colors.Color(0.5,0.5,0.5), colors.Color(0,0,0))
    return gm.ProcessFile(f_overlay)


def producePrintoutsForLayer(path, layer, canv, file_name):
    ctmp = canvas.Canvas(file_name)
    ext = renderGerber(path, layer, ctmp)

    scale1 = (gerberPageSize[0]-2*gerberMargin)/((ext[2]-ext[0]))
    scale2 = (gerberPageSize[1]-2*gerberMargin)/((ext[3]-ext[1]))
    scale = min(scale1, scale2)
    gerberScale = (scale,scale)
#    print("PS" , gerberPageSize[0], gerberMargin, gerberScale)
    gerberOffset = (-ext[0]*scale + gerberMargin, -ext[1]*scale + gerberMargin)
#    print "Offset (in.): (%4.2f, %4.2f)" % (gerberOffset[0]/inch,gerberOffset[1]/inch)
#    print "Scale (in.):  (%4.2f, %4.2f)" % gerberScale
    pf = PickAndPlaceFileKicad(findFileInDir(path, ".csv"))
    ngrp =  pf.num_groups(layer)
    print(ngrp)

    for page in range(0, (ngrp+5)/6):
        n_comps = min(6, ngrp - page*6)

        canv.saveState()
        canv.translate( gerberOffset[0], gerberOffset[1] )
        if(layer == "bottom"):
            canv.scale( gerberScale[0], gerberScale[1] )
            canv.scale( -1, 1 )
            canv.translate(-0.4*gerberPageSize[0],0)
        else:
            canv.scale( gerberScale[0], gerberScale[1] )

        renderGerber(path, layer, canv)

        pf.draw(layer, page*6, n_comps, canv)

        canv.restoreState()
        pf.gen_table(layer, page*6, n_comps, canv)
        canv.showPage()

import argparse
import os
import tempfile
import shutil
import atexit

class valid_directory(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir=values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError("valid_directory:{0} is not a valid path".format(prospective_dir))
        if os.access(prospective_dir, os.R_OK):
            setattr(namespace,self.dest,prospective_dir)
        else:
            raise argparse.ArgumentTypeError("valid_directory:{0} is not a readable dir".format(prospective_dir))

ldir = tempfile.mkdtemp()
atexit.register(lambda dir=ldir: shutil.rmtree(ldir))

parser = argparse.ArgumentParser(description='Generate a PDF file for pick and place assembly')
#parser.add_argument('path', help='Path to input files (GBL, GBO, GTL, GTO and CSV) directory', action=valid_directory)
parser.add_argument('--path', help='Path to input files (GBL, GBO, GTL, GTO and CSV) directory', default = dirname)
parser.add_argument('--o', '--output', type=str, metavar='<filename>', help='Specify the output file name')

args = parser.parse_args()

if args.o != None:
    file_name = args.path+'/'+args.o
else:
    file_name = args.path+"/assygen.pdf"

print("Path: "+args.path)
print("Output file name: "+file_name)

canv = canvas.Canvas(file_name)

producePrintoutsForLayer(args.path, "T", canv, file_name)
producePrintoutsForLayer(args.path, "B", canv, file_name)
canv.save()