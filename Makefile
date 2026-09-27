# Montage video - Clair net enrichi
#
#   make video EP=EP001        episode complet, 1920x1080 30 i/s
#   make preview EP=EP001      meme montage en 960x540, pour verifier vite
#   make plans EP=EP001 S=S01  ne rendre qu'un plan (S accepte plusieurs ids)
#   make rebuild EP=EP001      remonter sans refaire les rendus deja faits
#   make check EP=EP001        ecrire et afficher la timeline, sans aucun rendu
#   make scene EP=EP001 S=S06  un seul plan, basse qualite (alias de plans)
#   make draft EP=EP001        episode complet en basse qualite (alias de preview)
#   make clean EP=EP001        effacer les fichiers intermediaires
#
# Prerequis : python, manim, ffmpeg. L'audio de l'episode doit deja exister
# (audio/Sxx.wav + audio/durations.json), c'est la skill Cowork qui le produit.

PY ?= python
LOCALE ?= fr
EP ?=
S  ?=

ifeq ($(EP),)
$(error precisez l'episode : make video EP=EP001)
endif

.PHONY: video preview plans rebuild clean check scene draft

video:
	$(PY) video/build.py --ep $(EP) --locale $(LOCALE)

preview:
	$(PY) video/build.py --ep $(EP) --preview --locale $(LOCALE)

plans:
	$(PY) video/build.py --ep $(EP) --only $(S) --preview --locale $(LOCALE)

check:
	$(PY) video/build.py --ep $(EP) --check

scene: plans

draft: preview

rebuild:
	$(PY) video/build.py --ep $(EP) --skip-render --locale $(LOCALE)

clean:
	rm -rf episodes/$(EP)/video/plans episodes/$(EP)/video/plans_cales \
	       episodes/$(EP)/video/_manim episodes/$(EP)/video/_check \
	       episodes/$(EP)/video/voix.wav
