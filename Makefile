SHELL           := /usr/bin/zsh

### ---------------------------------------------------
### Icons
### ---------------------------------------------------
ICONS_FOLDER	:= assets/icons
ICONS		+= simple/github simple/googlecolab simple/googleslides

### ---------------------------------------------------
### Make Documentation
### ---------------------------------------------------
ENV 		:= emacs
CONDA_ROOT	:= ~/miniconda3

# HOST left blank to enable the default defined in the
# underlying toolkit
HOST		:=

# The default behaviour for PORT in this Makefile is
# defined to use a random 4-digit port.  To use a
# specific port use PORT=NNNN while invocation.  To
# revert to default behaviour of the underlying
# toolkit, explicitly invoke with empty value,
# i.e. PORT="".
PORT		:=
localport	 = $(shell				\
  echo $$(( 1000 + ($$RANDOM % 9000) ))			\
)

# Use `ADDR="HOST:PORT"' as a shorthand instead of
# `HOST="HOST" PORT="PORT"'
ADDR		:= $(and $(or $(HOST),$(PORT)),		\
  $(or $(HOST),localhost):$(or $(PORT),$(localport))	\
)
ADDR_SWITCH	:= $(and $(ADDR),-a $(ADDR))

PYTHONPATH	:= $${PYTHONPATH}:$${PWD}:$${PWD}/src

mkdocs		+= source $(CONDA_ROOT)/bin/activate
mkdocs		+= $(ENV) ; PYTHONPATH=$(PYTHONPATH)
mkdocs		+= mkdocs

docserve : icons
	$(mkdocs) serve $(ADDR_SWITCH) --livereload

docbuild : icons
	$(mkdocs) build

docs : docserve

icons : $(ICONS_FOLDER) ${ICONS:%=$(ICONS_FOLDER)/%.svg}
$(ICONS_FOLDER)/simple/%.svg: $(ICONS_FOLDER)/simple
	wget "https://simpleicons.org/icons/$(*).svg" 	\
	  -O $(@)

$(ICONS_FOLDER)/simple $(ICONS_FOLDER) :
	mkdir -p $(@)
### ---------------------------------------------------

### ---------------------------------------------------
### Pawan
### ---------------------------------------------------
### The daily job runs these in the same order. Handy for
### reproducing a day's output locally when something looks off.

.PHONY: ingest eval forecast site daily check history compare report

ingest:
	python code/ingest/run_daily.py

eval:
	python code/evaluate.py

forecast:
	python code/predict.py

site:
	python code/pages.py

# Everything, in the order the workflow does it.
daily: ingest eval forecast site

check:
	ruff check code/ scripts/
	python -m pytest code/tests/ -q

# One-off: the record back to the start of the live sensor, then
# weather and fires for the new rows. Normally run from the
# "Extend history" workflow instead, so daily.csv is written on
# GitHub and there is no merge to untangle.
history:
	python scripts/extend_history.py
	python scripts/backfill_history.py --force

# Candidate burning-season models against the current one. Reads
# daily.csv, writes nothing.
compare:
	python scripts/compare_models.py

# The prototype report: regenerate its numbers from data/, then
# build the PDF.
report:
	python scripts/report_figures.py
	cd project-report-prototype-stage && latexmk -pdf main.tex
