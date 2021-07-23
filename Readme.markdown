# Göktuğ’s Gemini Scripts

This is a catch-all repository for my scripts related to the new
[Gemini protocol](https://gemini.circumlunar.space).

This work, including this document, is licensed under the Cooperative
Non-Violent Public License, version 6 or newer, whose text is
available in the [LICENSE](./LICENSE) file in this repository, or
online at <https://git.pixie.town/thufie/CNPL>.  In case the local and
online versions differ, the more recent version applies.

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
Flask and Ignition libraries.

`g2ra.py` can also be used as a command line app to generate a feed,
given a gemlog index file.

**Major caveat**: currently does not handle Gemini redirects.

### Command line frontend

#### Generate static feeds from local files

This could come in handy for you if you are auto-generating a HTML
version of your gemlog.  The operation is simple:

    % g2ra.py static -u my.url -t atom -a "Author" -p path/to/index.gmi

See `g2ra.py static --help` for more info.  The Flask frontend is more
lenient when it comes to default values for parameters, command line
frontend has a couple more required ones.

#### Run test server

You can run a test server as follows:

    % g2ra.py flask

This will start a local CGI server you can use.


### Proxy frontend

I may one day deploy this on some public server (go ahead if you want to
do so yourself, patches welcome!), but as it is now, you are expected to
deploy this script on some server yourself.  It should be fairly easy to
do using [usual Flask deployment
options](https://flask.palletsprojects.com/en/1.1.x/deploying/index.html),
and below are instructions on how to set it up with Gunicorn and
virtualenvs as a local service.

First of all, create a virtual environment:

    % mkdir g2ra-deploy
    % cd g2ra-deploy
    % python3 -m venv venv

Activate the virtual environment and install dependencies:

    % source venv/bin/activate
    % pip3 install gunicorn flask ignition-gemini

Test the script is running alright:

    % # copy g2ra.py here
    % gunicorn -b 127.0.0.1:1961 'g2ra:flask_app("__main__")'
    % curl 'localhost:1961?url=cadadr.space/blag.gmi'

Write a simple script you run at login:

    % cd ..
    % cp -r g2ra-deploy ~/local/g2ra-deploy
    % cat <<EOF > ~/bin/start-g2ra.sh
    > #!/bin/sh
    > cd ~/local/g2ra-deploy
    > ./venv/bin/python -m gunicorn -b 127.0.0.1:1961 'g2ra:flask_app("__main__")'
    > EOF
    %

Here on you can use any of `~/.config/autostart`, user systemd units,
cron, `.xinitrc`, etc to run this script.

Another likely option is to run this as a (Fast)CGI script using a local
installation of some web server.  I haven't set that up yet, but
following flask instruction should be enough.  I might extend this
tutorial later with relevant info.

The usage of `g2ra.py` is simple.  You will use a combination of the
the following query parameters:

- `url`: **mandatory**, the gemini **page** to convert.  `g2ra` does not do
  redirects yet, so you need the full path to a gemini page.

- `type`: optional, can be either of `atom` or `rss`.  The former is the
  default, and causes the page to be converted to an Atom feed.  The
  latter will lead to an RSS feed being generated.

- `author`: Author field for Atom scripts' mandatory `<author>` fields.
  The default value is `Unknown Author Jr.`.

- `ttl`: Time to live attribute for RSS channels (the `<ttl>` tag),
  defaults to 1800.

