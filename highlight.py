# This file is part of the qpageview package.
#
# Copyright (c) 2010 - 2019 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.


"""
Highlight rectangular areas inside a View.
"""

from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QApplication


class Highlighter:
    """A Highlighter can draw rectangles to highlight e.g. links in a View.

    An instance represents a certain type of highlighting, e.g. of a particular 
    style. The paintRects() method is called with a list of rectangles that 
    need to be drawn.

    To implement different highlighting behaviour just inherit paintRects(). 
    The default implementation of paintRects() uses the `color` attribute to get 
    the color to use and the `lineWidth` (default: 2) and `radius` (default: 3) 
    attributes.

    `lineWidth` specifies the thickness in pixels of the border drawn, `radius` 
    specifies the distance in pixels the border is drawn (by default with 
    rounded corners) around the area to be highlighted. `color` is set to None
    by default, causing the paintRects method to choose the application's
    palette highlight color.

    """

    lineWidth = 2
    radius = 3
    color = None

    def paintRects(self, painter, rects):
        """Override this method to implement different drawing behaviour."""
        color = self.color if self.color is not None else QApplication.palette().highlight().color()
        pen = QPen(color)
        pen.setWidth(self.lineWidth)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rad = self.radius
        for r in rects:
            r.adjust(-rad, -rad, rad, rad)
            painter.drawRoundedRect(r, rad, rad)


