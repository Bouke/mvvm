from mvvm.viewbinding.display import StatusBarBinding, TitleBinding, LabelBinding
from demo.ui_generated import BaseDemoFrame
from demo.viewmodel import DemoViewModel
from mvvm.viewbinding.interactive import TextBinding


class DemoFrame(BaseDemoFrame):
    def __init__(self, parent):
        super(DemoFrame, self).__init__(parent)

        self.viewmodel = DemoViewModel()
        self.bindings = [
            TextBinding(self.text_title, (self.viewmodel, 'title')),
            TextBinding(self.text_statusbar, (self.viewmodel, 'statusbar')),
            TextBinding(self.text_label, (self.viewmodel, 'label')),

            TitleBinding(self, (self.viewmodel, 'title')),
            StatusBarBinding(self.statusbar, (self.viewmodel, 'statusbar'), 1),
            LabelBinding(self.label_label, (self.viewmodel, 'label')),
        ]
