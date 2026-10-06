"""Keep CI recipes compatible with their namespaced crafting components."""
from pathlib import Path
import copy
import xml.etree.ElementTree as E

data = Path(__file__).resolve().parents[1] / 'module/CIItemLab/ModuleData'
native = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules\Native\ModuleData')
templates = E.parse(data / 'lab_crafting_templates.xml')
descriptions = E.parse(data / 'lab_weapon_descriptions.xml')
pieces = {e.get('id') for e in E.parse(data / 'lab_crafting_pieces.xml').getroot()}
native_templates = {e.get('id'): e for e in E.parse(native / 'crafting_templates.xml').getroot()}
native_descriptions = {e.get('id'): e for e in E.parse(native / 'weapon_descriptions.xml').getroot()}
available = pieces | {e.get('id') for e in E.parse(native / 'crafting_pieces.xml').getroot()}
known = {e.get('id') for e in templates.getroot()}
for file in (data / 'labitems').glob('*.xml'):
    tree = E.parse(file)
    changed = False
    for item in tree.getroot().findall('CraftedItem'):
        original = item.get('crafting_template')
        if original not in native_templates:
            continue
        tid = 'cilab_recipe_template_' + original
        if tid not in known:
            template = copy.deepcopy(native_templates[original])
            template.set('id', tid)
            mapping = {}
            for ref in template.findall('./WeaponDescriptions/WeaponDescription'):
                old = ref.get('id')
                desc = copy.deepcopy(native_descriptions[old])
                did = 'cilab_recipe_desc_' + original + '_' + old
                desc.set('id', did)
                mapping[old] = did
                ref.set('id', did)
                for p in desc.findall('./AvailablePieces/AvailablePiece'):
                    if 'cilab_' + p.get('id') in pieces:
                        p.set('id', 'cilab_' + p.get('id'))
                descriptions.getroot().append(desc)
            for stats in template.findall('StatsData'):
                if stats.get('weapon_description') in mapping:
                    stats.set('weapon_description', mapping[stats.get('weapon_description')])
            for p in template.findall('./UsablePieces/UsablePiece'):
                if 'cilab_' + p.get('piece_id') in pieces:
                    p.set('piece_id', 'cilab_' + p.get('piece_id'))
            templates.getroot().append(template)
            known.add(tid)
        item.set('crafting_template', tid)
        changed = True
    if changed:
        E.indent(tree)
        tree.write(file, encoding='utf-8', xml_declaration=True)
for tree, name in [(templates, 'lab_crafting_templates.xml'), (descriptions, 'lab_weapon_descriptions.xml')]:
    for parent in tree.getroot().iter():
        for child in list(parent):
            key = 'piece_id' if child.tag == 'UsablePiece' else 'id' if child.tag == 'AvailablePiece' else None
            if key and child.get(key) not in available:
                parent.remove(child)
    E.indent(tree)
    tree.write(data / name, encoding='utf-8', xml_declaration=True)
print('Namespaced native recipes repaired.')
