# spaceh.awk --- gemini to html

# Copyright (C) 2021  Göktuğ Kayaalp <self at gkayaalp dot com>
#
# This file is part of Pomodorino.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.



# set mode vars, print header
BEGIN {
    inpre = 0;
    inlist = 0;
    inbq = 0;

    while ((getline l < (header ? header : "header.html")) > 0) {
        print l;
    }
}

# html escape
function html_escape (x) {
    a = gensub(/&/, "\\&amp;", "g", x);
    b = gensub(/^(.+)>/, "\\1\\&gt;", "g", a);
    c = gensub(/^(.+)</, "\\1\\&lt;", "g", b);
    return c;
}

function chomp (x) {
    a = gensub(/^[[:space:]]+/, "", "g", x);
    b = gensub(/[[:space:]]+$/, "", "g", a);
    return b;
}


# preformatted block
/^```/,!/^```/ {
    if ($1 == "```" && !inpre) {
        $1 = "";
        inpre = 1;
	title = chomp(html_escape($0));
	if(title != "")
	    printf("%s%s%s\n", "<pre title='", chomp(html_escape($0)) ,"'>");
	else
	    print("<pre>");
    }
    else if ($1 == "```") {
        inpre = 0;
        print("</pre>");
    }
    else
        print(html_escape($0));
    next;
}

# link
/^=>/ {
    if ($2 !~ /^[a-z]+:\/\//) {
        $2 = gensub(/^\.\//, "", "g", $2);
        $2 = gensub(/\.gmi$/, ".html", "g", $2);
    }

    printf("<a href='%s'>", html_escape($2));

    # print link description
    if (NF == 2)
        printf(html_escape($2));
    else
        for (i=3; i<=NF; i++) {
            printf(html_escape($i));
            if (i != NF)
                printf(" ");
        }

    print("</a><br/>");
    next;
}


# blockquote
/^> / && !inbq {
    $1 = "";
    inbq = 1;
    print("<blockquote>", html_escape($0));
    next;
}
/^> / && inbq {
    $1 = "";
    print("<br/>", html_escape($0));
    next;
}
/^\s*$/ && inbq {
    inbq = 0;
    print("</blockquote>\n");
    next;
}

# headlines
/^# /   { $1 = ""; print("<h1>", html_escape($0), "</h1>"); next; }
/^## /  { $1 = ""; print("<h2>", html_escape($0), "</h2>"); next; }
/^### / { $1 = ""; print("<h3>", html_escape($0), "</h3>"); next; }

# lists
/^\* / && !inlist {
    $1 = "";
    inlist = 1;
    print("<ul>\n<li>", html_escape($0), "</li>");
    next;
}
/^\* / && inlist {
    $1 = "";
    print("<li>", html_escape($0), "</li>");
    next;
}
/^\s*$/ && inlist {
    inlist = 0;
    print("</ul>\n");
    next;
}

# catch all
/^\s*$/ && !inpre { print(""); next; } # one \n for blank line
/.*/    && inpre  { print(html_escape($0)); next; }
# custom: centre asterisms
/^ +⁂/  && !inpre { print("<p align='center'>",
                          html_escape($0), "</p>"); next; }
/.*/    && !inpre { print("<p>", html_escape($0), "</p>"); next; }

# close open blocks, if any; then print footer.
END {
    if (inlist) print("</ul>");
    if (inbq)   print("</blockquote>");
    if (inpre)  print("</pre>");

    while ((getline l < (footer ? footer : "footer.html")) > 0) {
        print l;
    }
}
