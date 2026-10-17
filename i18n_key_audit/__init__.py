"""Find translation keys that are missing, unused, or absent from a locale.

None of these break a build. They surface as a raw key on a user's screen,
a paid translation nobody renders, or a feature that silently stays English
for everyone outside the base locale.
"""

__version__ = "0.1.0"
