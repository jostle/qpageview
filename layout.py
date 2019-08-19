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
Manages and positions a group of Page instances.
"""


import collections
import copy

from PyQt5.QtCore import QMargins, QPoint, QPointF, QRect, QSize

from . import rectangles
from .constants import (
    FixedScale,
    FitWidth,
    FitHeight,
    FitBoth,

    Rotate_0,
    Rotate_90,
    Rotate_180,
    Rotate_270,

    Horizontal,
    Vertical,
)


class PageRects(rectangles.Rectangles):
    def get_coords(self, page):
        return page.geometry().getCoords()


class AbstractPageLayout(list):
    """Manages page.Page instances with a list-like api.

    You can iterate over the layout itself, which yields all Page instances.

    The following instance attributes are used, with these class-level defaults:

        _margins = (6, 6, 6, 6) # margins around layout, access via margins()
        spacing = 8             # pixels between pages
        zoomFactor = 1.0
        dpiX = 72.0
        dpiY = 72.0
        rotation = Rotate_0

        x = 0                   # x, y, width and height are set by update()
        y = 0
        width = 0
        height = 0

        continuousMode = True   # whether to show all pages
        pagesPerSet = 1         # if not, how many pages per set
        pagesFirstSet = 0       # how many pages in first set
        currentPageSet = 0      # which page set to display

    After having changed pages or layout attributes, call update() to update
    the layout.

    """

    _margins = (6, 6, 6, 6)
    spacing = 8
    zoomFactor = 1.0
    dpiX = 72.0
    dpiY = 72.0
    rotation = Rotate_0
    x = 0
    y = 0
    width = 0
    height = 0

    continuousMode = True
    pagesPerSet = 1
    pagesFirstSet = 0
    currentPageSet = 0

    _rects = None

    def __bool__(self):
        """Always return True."""
        return True

    def count(self):
        """Return the number of Page instances."""
        return len(self)

    def empty(self):
        """Return True if there are zero pages."""
        return len(self) == 0

    def copy(self):
        """Return a copy of this layout with copies of all the pages."""
        layout = copy.copy(self)
        layout[:] = (p.copy() for p in self)
        return layout

    def setPos(self, point):
        """Set our top-left coordinate of the visible geometry."""
        self.x = point.x()
        self.y = point.y()

    def pos(self):
        """Return the top-left coordinate of the visible geometry.

        Normally this is QPoint(0, 0), but when a non-continuous mode is
        used it can be different: the top-left corner of the visible page set
        area.

        """
        return QPoint(self.x, self.y)

    def setGeometry(self, rect):
        """Set the rectangle describing the visible part of the layout."""
        self.x, self.y, self.width, self.height = rect.getRect()

    def geometry(self):
        """Return the rectangle describing the visible part of the layout."""
        return QRect(self.x, self.y, self.width, self.height)

    def setSize(self, size):
        """Set our size. Normally done after layout by computeSize()."""
        self.width = size.width()
        self.height = size.height()

    def size(self):
        """Return our size as QSize()."""
        return QSize(self.width, self.height)

    def setMargins(self, margins):
        """Sets our margins to a QMargins object."""
        self._m = margins

    def margins(self):
        """Return our margins as a QMargins object, intialized from _margins"""
        try:
            return self._m
        except AttributeError:
            self._m = QMargins(*self._margins)
            return self._m
    
    def _pageRects(self):
        """(Internal) Return the PageRects object for quickly finding pages."""
        if self._rects:
            return self._rects
        r = self._rects = PageRects(self.displayPages())
        return r

    def pageAt(self, point):
        """Return the page that contains the given QPoint.

        If the point is not on any page, None is returned.

        """
        for page in self._pageRects().at(point.x(), point.y()):
            return page

    def pagesAt(self, rect):
        """Yield the pages touched by the given QRect.

        The pages are in undefined order.

        """
        for page in self._pageRects().intersecting(*rect.getCoords()):
            yield page

    def nearestPageAt(self, point):
        """Return the page at the shortest distance from the given point.

        The returned page does not contain the point. (Use pageAt() for that.)
        If there are no pages outside the point, None is returned.

        """
        return self._pageRects().nearest(point.x(), point.y())

    def widestPage(self):
        """Return the widest page, if any.

        Uses the page's natural width and its scale in X-direction.

        """
        if self.count():
            def key(page):
                psize = page.pageSize()
                if (page.rotation + self.rotation) & 1:
                    return psize.height() * page.scaleY
                else:
                    return psize.width() * page.scaleX
            return max(self, key=key)

    def highestPage(self):
        """Return the highest page, if any.

        Uses the page's natural height and its scale in Y-direction.

        """
        if self.count():
            def key(page):
                psize = page.pageSize()
                if (page.rotation + self.rotation) & 1:
                    return psize.width() * page.scaleX
                else:
                    return psize.height() * page.scaleY
            return max(self, key=key)

    def fit(self, size, mode):
        """Fits the layout in the given size (QSize) and ViewMode."""
        if mode and self.count():
            zoomfactors = []
            if mode & FitWidth:
                zoomfactors.append(self.zoomFitWidth(size.width()))
            if mode & FitHeight:
                zoomfactors.append(self.zoomFitHeight(size.height()))
            self.zoomFactor = min(zoomfactors)

    def zoomFitWidth(self, width):
        """Return the zoom factor this layout would need to fit in the width.

        This method is called by fit(). The default implementation returns a
        suitable zoom factor for the widest Page.

        """
        width -= self.margins().left() + self.margins().right()
        return self.widestPage().zoomForWidth(width, self.rotation, self.dpiX)

    def zoomFitHeight(self, height):
        """Return the zoom factor this layout would need to fit in the height.

        This method is called by fit(). The default implementation returns a
        suitable zoom factor for the highest Page.

        """
        height -= self.margins().top() + self.margins().bottom()
        return self.highestPage().zoomForHeight(height, self.rotation, self.dpiY)

    def update(self):
        """Compute the size of all pages and updates their positions.
        Finally set our own size.

        You should call this after having added or deleted pages or after
        having changed the scale, dpi, zoom factor, spacing or margins.

        This function returns True if the total geometry has changed.

        """
        self._rects = None
        self.updatePageSizes()
        self.updatePagePositions()
        geometry = self.computeGeometry()
        changed = self.geometry() != geometry
        self.setGeometry(geometry)
        return changed

    def updatePageSizes(self):
        """Compute the correct size of every Page."""
        for page in self:
            page.computedRotation = rotation = (page.rotation + self.rotation) & 3
            page.width, page.height = page.computeSize(
                rotation, self.dpiX, self.dpiY, self.zoomFactor)

    def updatePagePositions(self):
        """Determine the position of every Page.

        You should implement this method to perform a meaningful layout, which
        means setting the position of all the pages. This positions should
        respect the margin (and preferably also the spacing).

        """
        top = self.margins().top()
        for page in self:
            page.x = self.margins().left()
            page.y = top
            top += page.height
            top += self.spacing

    def computeGeometry(self):
        """Return the total geometry (position and size) of the layout.

        In most cases the implementation of this method is sufficient: it
        computes the bounding rectangle of all Pages and adds the margin.

        """
        r = QRect()
        for page in self.displayPages():
            r |= page.geometry()
        return r + self.margins()

    def pos2offset(self, pos):
        """Return a three-tuple (index, x, y).

        The index refers to a page in the layout, or nowhere if -1. The x and y
        refer to a spot on the page (or layout if empty) in the range 0..1.
        You can use it to store a certain position and restore it after
        changing the zoom e.g.

        """
        page = self.pageAt(pos) or self.nearestPageAt(pos)
        if page:
            pos = pos - page.pos()
            w = page.width
            h = page.height
            i = self.index(page)
        else:
            w = self.width
            h = self.height
            i = -1
        x = pos.x() / w
        y = pos.y() / h
        return (i, x, y)

    def offset2pos(self, offset):
        """Return the pos on the layout for the specified offset.

        The offset is a three-tuple like returned by pos2offset().

        """
        i, x, y = offset
        if i < 0 or i >= len(self):
            pos = QPoint(0, 0)
            w = self.width
            h = self.height
        else:
            page = self[i]
            pos = page.pos()
            w = page.width
            h = page.height
        return pos + QPoint(round(x * w), round(y * h))

    def displayPages(self):
        """Return the pages that are to be displayed.

        If continuousMode is True, simply returns self, to show all pages.
        If not, reads the currentPageSet attribute and uses the pageSets()
        method to determine the set of pages to restrict the display to.

        """
        if not self.continuousMode:
            num = self.currentPageSet
            count = self.pageSetCount()
            # make sure a valid slice is returned
            if num and num >= count:
                num = self.currentPageSet = count - 1
            p = 0
            s = 0
            for count, length in self.pageSets():
                if p + count <= num:
                    p += count
                    s += count * length
                    continue
                count = num - p
                s += count * length
                return self[s:s+length]
        return self

    def pageSets(self):
        """Return a list of (count, length) tuples.

        Every count is the number of page sets of that length. The sum of all
        (count * length) should be the total length of the layout. If the layout
        is empty, an empty list is returned.

        The default implementation reads the pagesFirstSet and pagesPerSet
        attributes, and returns at most three tuples.

        All other pageSet methods use the result of this method for their
        computations.

        """
        result = []
        left = self.count()
        if left:
            if self.pagesFirstSet and self.pagesFirstSet != self.pagesPerSet:
                length = min(left, self.pagesFirstSet)
                result.append((1, length))
                left -= length
            if left:
                count, left = divmod(left, self.pagesPerSet)
                if count:
                    result.append((count, self.pagesPerSet))
                if left:
                    # merge result entries with same length
                    if result and result[-1][1] == left:
                        result[-1] == (result[-1][0] + 1, left)
                    else:
                        result.append((1, left))
        return result

    def pageSetCount(self):
        """Return the number of page sets."""
        return sum(count for count, length in self.pageSets())

    def pageSet(self, index):
        """Return the page set containing page at index."""
        s = 0   # the index at the start of the last page set
        p = 0   # the page set
        for count, length in self.pageSets():
            if s + count * length < index:
                s += count * length
                p += count
                continue
            return p + (index - s) // length
        return 0    # happens with empty layout


class PageLayout(AbstractPageLayout):
    """A basic layout that shows pages from right to left or top to bottom.

    Additional instance attribute:

        `orientation`: Horizontal or Vertical (default)

    """
    orientation = Vertical

    def updatePagePositions(self):
        """Order our pages."""
        if self.orientation == Vertical:
            width = max((p.width for p in self), default=0)
            width += self.margins().left() + self.margins().right()
            top = self.margins().top()
            for page in self:
                page.x = (width - page.width) / 2
                page.y = top
                top += page.height + self.spacing
        else:
            height = max((p.height for p in self), default=0)
            height += self.margins().top() + self.margins().bottom()
            left = self.margins().left()
            for page in self:
                page.x = left
                page.y = (height - page.height) / 2
                left += page.width + self.spacing


class RowPageLayout(AbstractPageLayout):
    """A layout that orders pages in rows.

    Additional instance attributes:

        `pagesPerRow`     = 2, the number of pages to display in a row
        `pagesFirstRow`   = 1, the number of pages to display in the first row
        `fitAllColumns`   = True, whether "fit width" uses all columns

    The `pagesFirstSet` and `pagesPerSet` instance attributes are changed to
    properties that automatically use the respective values of pagesFirstRow
    and pagesPerRow.

    """

    pagesPerRow = 2
    pagesFirstRow = 1
    fitAllColumns = True

    @property
    def pagesPerSet(self):
        return self.pagesPerRow

    @property
    def pagesFirstSet(self):
        return self.pagesFirstRow

    def zoomFitWidth(self, width):
        """Reimplemented to respect the fitAllColumns setting."""
        width -= self.margins().left() + self.margins().right()
        if self.fitAllColumns:
            ncols = min(self.pagesPerRow, self.count())
            width = (width - self.spacing * (ncols - 1)) // ncols
        return self.widestPage().zoomForWidth(width, self.rotation, self.dpiX)

    def updatePagePositions(self):
        """Reimplemented to perform our positioning algorithm."""
        pages = list(self)
        cols = self.pagesPerRow
        if len(pages) > cols:
            ## prepend empty places if the first row should display less pages
            pages[0:0] = [None] * ((cols - self.pagesFirstRow) % cols)
        else:
            cols = len(pages)

        col_widths = []
        col_offsets = []
        offset = self.margins().left()
        for col in range(cols):
            width = max(p.width for p in pages[col::cols] if p)
            col_widths.append(width)
            col_offsets.append(offset)
            offset += width + self.spacing

        top = self.margins().top()
        for row in (pages[i:i + cols] for i in range(0, len(pages), cols or 1)):
            height = max(p.height for p in row if p)
            for n, page in enumerate(row):
                if page:
                    page.x = col_offsets[n] + (col_widths[n] - page.width) // 2
                    page.y = top + (height - page.height) // 2
            top += height + self.spacing


