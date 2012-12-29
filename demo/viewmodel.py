from traits.has_traits import HasTraits
from traits.trait_types import Str


class DemoViewModel(HasTraits):
    title = Str('MVVM Demo')
    statusbar = Str('Change me!')
    label = Str('Label')
