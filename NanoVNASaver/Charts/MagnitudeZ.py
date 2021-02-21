#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import math
import logging
from typing import List

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.RFTools import Datapoint
from .Frequency import FrequencyChart
from .LogMag import LogMagChart


logger = logging.getLogger(__name__)


class MagnitudeZChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            if self.logarithmicY and minValue <= 0:
                self.minValue = 0.01
            else:
                self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = 0
            for d in self.data:
                mag = self.magnitude(d)
                if math.isinf(mag): # Avoid infinite scales
                    continue
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                mag = self.magnitude(d)
                if math.isinf(mag): # Avoid infinite scales
                    continue
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag

            minValue = 10*math.floor(minValue/10)
            if self.logarithmicY and minValue <= 0:
                minValue = 0.01
            self.minValue = minValue

            maxValue = 10*math.ceil(maxValue/10)
            self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)

        for i in range(1, target_ticks):
            val = minValue + (i / target_ticks) * self.span
            if self.logarithmicY:
                y = self.topMargin + (self.maxValue - val) / self.span * self.chartHeight
                val = self.valueAtPosition(y)[0]
            else:
                y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)

            qp.setPen(self.textColor)
            digits = max(0, min(2, math.floor(5 - math.log10(abs(val)))))
            if digits == 0:
                vswrstr = str(round(val))
            else:
                vswrstr = str(round(val, digits))
            qp.drawText(3, y + 3, vswrstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        mag = self.magnitude(d)
        if self.logarithmicY and mag == 0:
            return self.topMargin - self.chartHeight
        if math.isfinite(mag):
            if self.logarithmicY:
                span = math.log(self.maxValue) - math.log(self.minValue)
                return self.topMargin + round((math.log(self.maxValue) - math.log(mag)) / span * self.chartHeight)
            return self.topMargin + round((self.maxValue - mag) / self.span * self.chartHeight)
        else:
            return self.topMargin

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            span = math.log(self.maxValue) - math.log(self.minValue)
            val = math.exp(math.log(self.maxValue) - absy * span / self.chartHeight)
        else:
            val = self.maxValue - (absy / self.chartHeight * self.span)
        return [val]

    @staticmethod
    def magnitude(p: Datapoint) -> float:
        return abs(p.impedance())

    def logarithmicYAllowed(self) -> bool:
        return True;

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.span = self.span
        return new_chart
