# spaceh.awk --- gemini to html

# Copyright (c) 2021 Göktuğ Kayaalp

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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
