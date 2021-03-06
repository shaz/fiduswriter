/**
 * This file is part of Fidus Writer <http://www.fiduswriter.org>
 *
 * Copyright (C) 2013 Takuto Kojima, Johannes Wilm
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

(function () {
    var exports = this,
        printHelpers = {}, documentOwners=[];
        
    var pageSizes = {
        folio: {
            width:12,
            height:15
        },
        quarto: {
            width:9.5,
            height:12
        },
        octavo: {
            width:6,
            height:9
        },
        a5: {
            width:5.83,
            height:8.27
        },
        a4: {            
            width:8.27,
            height:11.69
        }
    };

    printHelpers.setTheBook = function (aBook) {
        var i;
        theBook = aBook;
        theBook.settings = jQuery.parseJSON(theBook.settings);
        theBook.metadata = jQuery.parseJSON(theBook.metadata);
        for (i = 0; i < theBook.chapters.length; i++) {
            theBook.chapters[i].metadata = jQuery.parseJSON(theBook.chapters[
                i].metadata);
            theBook.chapters[i].settings = jQuery.parseJSON(theBook.chapters[
                i].settings);
            if (documentOwners.indexOf(theBook.chapters[i].owner)===-1) {
                documentOwners.push(theBook.chapters[i].owner);
            }
        }
        paginationConfig['pageHeight'] = pageSizes[theBook.settings.papersize].height;
        paginationConfig['pageWidth'] = pageSizes[theBook.settings.papersize].width;

        bibliographyHelpers.getABibDB(documentOwners.join(','), function (
                aBibDB) {
                
            
                printHelpers.fillPrintPage(aBibDB);
            });
        

    };

    printHelpers.getBookData = function (id) {
        $.ajax({
            url: '/book/book/',
            data: {
                'id': id
            },
            type: 'POST',
            dataType: 'json',
            success: function (response, textStatus, jqXHR) {
                printHelpers.setTheBook(response.book);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                $.addAlert('error', jqXHR.responseText);
            },
            complete: function () {
                $.deactivateWait();
            }
        });
    };

    printHelpers.fillPrintPage = function (aBibDB) {
        jQuery(document.body).addClass(theBook.settings.documentstyle);
        jQuery('#book')[0].outerHTML = tmp_book_print({
            theBook: theBook
        });
        
        
        jQuery('#bibliography').html(citationHelpers.formatCitations(document.body, theBook.settings.citationstyle, aBibDB));
        

        paginationConfig['frontmatterContents'] = tmp_book_print_start({
            theBook: theBook
        });

        mathHelpers.resetMath(function () {
            pagination.initiate();
            pagination.applyBookLayout();
            jQuery("#pagination-contents").addClass('user-contents');
            jQuery('head title').html(jQuery('#document-title')[0].innerText);
        });
        
        
    };


    printHelpers.bind = function () {
        window.theBook = undefined;
        $(document).ready(function () {
            var pathnameParts = window.location.pathname.split('/'),
                bookId = parseInt(pathnameParts[pathnameParts.length -
                    2], 10);

            printHelpers.getBookData(bookId);
        });
    };


    exports.printHelpers = printHelpers;

}).call(this);