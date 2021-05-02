# Göktuğ’s Gemini Scripts

This is a catch-all repository for my scripts related to the new
[Gemini protocol](https://gemini.circumlunar.space).

## spaceh.awk

`spaceh.awk` converts Gemini files to HTML files.

    $ gawk -f spaceh.awk input.gmi > output.html

If either or both of `header.html` or `footer.html` are found in the
working directory, they are appended and prepended, respectively, to
`output.html`.

If you want to use other files as the header and/or the footer, you
can set the variables `header` and `footer` at the command line:

    $ gawk -v header=/path/to/header.html -v footer=/path/to/footer.html \
        -f spaceh.awk input.gmi > output.html

In order to convert a tree of Gemini files, you can use `find(1)` as
follows:

    find gemini -name '*.gmi' -exec sh -c 'gawk -v header=templates/header.html -v footer=templates/footer.html -f scripts/spaceh.awk {} > html/wormhole/$(basename -s .gmi {}).html' \;

Admittedly, that’s a gross command, so you might want to convert this
to a for loop and put it in a script instead.

## g2ra.py

`g2ra.py` is an RSS/Atom proxy for subscribable Gemini pages.  Uses
Flask and Ignition libraries.  WIP, incomplete.
