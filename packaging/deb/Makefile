#!/usr/bin/make -f
prefix=/usr

all:

install:
	cd data && find . -type f -exec install -D "{}" "$(DESTDIR)/{}" \;
	install -D -m 0754 $(CURDIR)/data/usr/bin/rocky-cli $(DESTDIR)/usr/bin/rocky-cli

clean:

distclean: clean

uninstall:
	-rm -f $(DESTDIR)/usr/local/bin/rocky-cli
	-rm -rf $(DESTDIR)/usr/share/kat-rocky

.PHONY: all install clean distclean uninstall

