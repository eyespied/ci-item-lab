"""Build a separate singleplayer item library from the locally installed CI pack."""
from pathlib import Path
import argparse, copy, json, re, shutil
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source', default=r'C:\Program Files (x86)\Steam\steamapps\workshop\content\261550\3245522442')
parser.add_argument('--game', default=r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')
args = parser.parse_args()
source = Path(args.source)
data = source / 'ModuleData'
dest = ROOT / 'module' / 'CIItemLab'
out = dest / 'ModuleData'
(out / 'labitems').mkdir(parents=True, exist_ok=True)
(dest / 'bin' / 'Win64_Shipping_Client').mkdir(parents=True, exist_ok=True)

groups = [
    ('mp_crafting_pieces.xml', 'CraftingPiece', 'lab_crafting_pieces.xml'),
    ('crafting_templates.xml', 'CraftingTemplate', 'lab_crafting_templates.xml'),
    ('weapon_descriptions.xml', 'WeaponDescription', 'lab_weapon_descriptions.xml'),
]
trees = [(f, ET.parse(f).getroot(), out / 'labitems' / f.name) for f in sorted((data / 'mpitems').rglob('*.xml'))]
trees += [(data / f, ET.parse(data / f).getroot(), out / target) for f, _, target in groups]
# Native multiplayer pieces are absent in Campaign. Import isolated copies for CI recipes.
piece_tree = next(r for f, r, target in trees if f.name == 'mp_crafting_pieces.xml')
ci_piece_ids = {e.get('id') for e in piece_tree}
native_data = Path(args.game) / 'Modules' / 'Native' / 'ModuleData'
native_mp = ET.parse(native_data / 'mp_crafting_pieces.xml').getroot()
for e in native_mp:
    if e.get('id') and e.get('id') not in ci_piece_ids:
        piece_tree.append(copy.deepcopy(e))
vanilla_piece_ids = {e.get('id') for e in ET.parse(native_data / 'crafting_pieces.xml').getroot()}
# Rename every definition so CI's variants cannot replace campaign or vanilla definitions.
maps = {}
for _, root, _ in trees:
    for e in root:
        if e.tag in ('Item', 'CraftedItem', 'CraftingPiece', 'CraftingTemplate', 'WeaponDescription'):
            maps.setdefault(e.tag, {})[e.get('id')] = 'cilab_' + e.get('id')
item_map = {**maps.get('Item', {}), **maps.get('CraftedItem', {})}
piece_map = maps.get('CraftingPiece', {})
template_map = maps.get('CraftingTemplate', {})
description_map = maps.get('WeaponDescription', {})
catalog, seen, duplicates, pruned = [], set(), [], []

def item_category(item):
    categories = {'HeadArmor':'Helmet', 'headArmor':'Helmet', 'BodyArmor':'Armor',
                  'Cape':'Shoulders', 'LegArmor':'Boots', 'HandArmor':'Gloves',
                  'Shield':'Shield', 'HorseHarness':'Harness', 'Horse':'Horse',
                  'Bow':'Bow', 'Crossbow':'Crossbow', 'Arrows':'Arrows', 'Bolts':'Bolts', 'Thrown':'Throwing'}
    if item.get('Type') in categories: return categories[item.get('Type')]
    usage = item.get('crafting_template', '')
    weapon = item.find('./ItemComponent/Weapon')
    if weapon is not None: usage += ' ' + weapon.get('weapon_class', '')
    for word,label in [('sword','Sword'),('axe','Axe'),('mace','Mace'),('lance','Polearm'),
                       ('polearm','Polearm'),('javelin','Throwing'),('dagger','Dagger')]:
        if word in usage.lower(): return label
    return 'Weapon'

def pack_name(filename):
    stem=filename.stem
    if stem[:2].isdigit(): return 'CI'
    return stem.split('_')[0]

def save(root, path):
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)

definition_seen = set()
for filename, root, target in trees:
    for e in list(root):
        if e.tag in ('Item', 'CraftedItem'):
            old_id = e.get('id')
            if old_id in seen:
                duplicates.append(old_id)
                root.remove(e)
                continue
            seen.add(old_id)
            original_name = re.sub(r'^\{=[^}]*\}', '', e.get('name', old_id))
            category, pack = item_category(e), pack_name(filename)
            display_name = f'[{category} | {pack}] {original_name} [{old_id}]'
            # Native inventory search matches displayed names. Literal names ensure that
            # localization keys cannot remove the lab's searchable labels.
            e.set('name', display_name)
            catalog.append({'id': item_map[old_id], 'original_id': old_id,
                            'name': display_name, 'original_name': original_name,
                            'category': category, 'pack': pack,
                            'type': e.get('Type', 'CraftedWeapon'), 'file': filename.name})
            e.attrib.pop('multiplayer_item', None)
            e.set('is_merchandise', 'false')
            if e.get('Type') == 'headArmor':
                e.set('Type', 'HeadArmor')
        if e.tag in maps and e.get('id') in maps[e.tag]:
            definition_key = (e.tag, e.get('id'))
            if definition_key in definition_seen:
                duplicates.append(e.tag + ':' + e.get('id'))
                root.remove(e)
                continue
            definition_seen.add(definition_key)
            e.set('id', maps[e.tag][e.get('id')])
        for n in e.iter():
            for key, value in list(n.attrib.items()):
                if key == 'culture' and value == 'Culture.neutral_culture':
                    n.set(key, 'Culture.empire')
                elif key == 'crafting_template' and value in template_map:
                    n.set(key, template_map[value])
                elif key == 'weapon_description' and value in description_map:
                    n.set(key, description_map[value])
                elif n.tag in ('Piece', 'AvailablePiece') and key == 'id' and value in piece_map:
                    n.set(key, piece_map[value])
                elif n.tag == 'UsablePiece' and key == 'piece_id' and value in piece_map:
                    n.set(key, piece_map[value])
                elif n.tag in ('WeaponDescription', 'UsableBy') and key == 'id' and value in description_map:
                    n.set(key, description_map[value])
                elif value.startswith('Item.') and value[5:] in item_map:
                    n.set(key, 'Item.' + item_map[value[5:]])
                elif key == 'difficulty':
                    n.set(key, '0')
    # Drop old optional smithing availability entries which refer to nonexistent pieces.
    # Actual CraftedItem recipes remain intact and are checked strictly by verify_lab.py.
    known_pieces = vanilla_piece_ids | set(piece_map.values())
    for parent in root.iter():
        for n in list(parent):
            ref = n.get('piece_id') if n.tag == 'UsablePiece' else n.get('id') if n.tag == 'AvailablePiece' else None
            if ref and ref not in known_pieces:
                pruned.append(ref)
                parent.remove(n)
    save(root, target)

# Engine data is loaded by its conventional filename, independently of XmlNodes.
for f in ['item_holsters.xml', 'item_usage_sets.xml', 'cloth_bodies.xml', 'module_sounds.xml']:
    if (data / f).exists():
        shutil.copy2(data / f, out / f)

module = ET.Element('Module')
for tag, val in [('Name', 'CI Item Lab (Singleplayer)'), ('Id', 'CIItemLab'),
                 ('Version', 'v0.3.0'), ('ModuleCategory', 'Singleplayer'),
                 ('SingleplayerModule', 'true'), ('MultiplayerModule', 'false')]:
    ET.SubElement(module, tag, value=val)
deps = ET.SubElement(module, 'DependedModules')
for id in ['Native', 'SandBoxCore', 'Sandbox']:
    ET.SubElement(deps, 'DependedModule', Id=id, Optional='false')
sub = ET.SubElement(ET.SubElement(module, 'SubModules'), 'SubModule')
for tag, val in [('Name', 'CI Item Lab'), ('DLLName', 'CIItemLab.dll'),
                 ('SubModuleClassType', 'CIItemLab.SubModule')]:
    ET.SubElement(sub, tag, value=val)
ET.SubElement(ET.SubElement(sub, 'Assemblies'), 'Assembly', value='0Harmony.dll')
tags = ET.SubElement(sub, 'Tags')
ET.SubElement(tags, 'Tag', key='DedicatedServerType', value='none')
ET.SubElement(tags, 'Tag', key='IsNoRenderModeElement', value='false')
xmls = ET.SubElement(module, 'Xmls')
for id, path in [('CraftingPieces', 'lab_crafting_pieces'), ('CraftingTemplates', 'lab_crafting_templates'),
                 ('WeaponDescriptions', 'lab_weapon_descriptions'), ('Items', 'labitems/')]:
    node = ET.SubElement(xmls, 'XmlNode')
    ET.SubElement(node, 'XmlName', id=id, path=path)
    included = ET.SubElement(node, 'IncludedGameTypes')
    for game in ['Campaign', 'CampaignStoryMode', 'CustomGame']:
        ET.SubElement(included, 'GameType', value=game)
save(module, dest / 'SubModule.xml')
(ROOT / 'docs' / 'item-catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
summary = {'source': str(source), 'items': len(catalog), 'duplicates_omitted': duplicates,
           'categories': dict(Counter(x['type'] for x in catalog)),
           'stale_optional_piece_references_omitted': sorted(set(pruned)),
           'crafting_pieces': len(piece_map), 'templates': len(template_map), 'weapon_descriptions': len(description_map)}
(ROOT / 'docs' / 'conversion-report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
