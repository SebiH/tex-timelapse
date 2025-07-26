from tex_timelapse.actions.action import Action
from tex_timelapse.project import Project
from tex_timelapse.snapshot import Snapshot, SnapshotStatus

import re

class ReplaceTextAction(Action):
    def getName(self) -> str:
        return 'Replace Text'

    def init(self, project: Project) -> None:
        self.text_replacements = project.config['text_replacements']

    def cleanup(self) -> None:
        pass

    def run(self, snapshot: Snapshot) -> str:
        work_dir = snapshot.getWorkDir()

        for file in snapshot.includes:
            if file.endswith('.tex') or file.endswith('.bib'):
                # replace text in the file
                file_path = f"{work_dir}/{file}"
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for replacement in self.text_replacements:
                    content = content.replace(replacement['old'], replacement['new'])
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        # remove any \includeonly statements from main tex file
        main_tex_file = snapshot.main_tex_file
        main_tex_path = f"{work_dir}/{main_tex_file}"
        with open(main_tex_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # remove \includeonly statements over multiple lines
            regex = r"^\s*%?\s*\\includeonly{.*?}"
            content = re.sub(regex, "", content, 0, re.MULTILINE | re.IGNORECASE | re.DOTALL)

        return SnapshotStatus.COMPLETED


    def reset(self, snapshot: Snapshot) -> None:
        pass
