"""Validate item IDs and crafting references against the installed vanilla data."""
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter
import json
import argparse

root = Path(__file__).resolve().parents[1]
data = root / 'module' / 'CIItemLab' / 'ModuleData'
parser=argparse.ArgumentParser()
parser.add_argument('--game', default=r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')
args=parser.parse_args()
game = Path(args.game)
known = {key:set() for key in ['Item','CraftedItem','CraftingPiece','CraftingTemplate','WeaponDescription','Culture','Monster']}
for module in ['Native','SandBoxCore','SandBox','StoryMode']:
    module_root=game / 'Modules' / module
    files=set()
    for node in ET.parse(module_root/'SubModule.xml').getroot().findall('./Xmls/XmlNode'):
        included=node.find('IncludedGameTypes')
        if included is not None and not any(e.get('value') in ['Campaign','CampaignStoryMode'] for e in included): continue
        path=node.find('XmlName').get('path')
        target=module_root/'ModuleData'/path
        if target.is_dir(): files.update(target.rglob('*.xml'))
        elif target.with_suffix('.xml').is_file(): files.add(target.with_suffix('.xml'))
    if (module_root/'ModuleData'/'monsters.xml').is_file(): files.add(module_root/'ModuleData'/'monsters.xml')
    for file in files:
        try: tree = ET.parse(file)
        except ET.ParseError: continue
        for e in tree.getroot().iter():
            if e.tag in known and e.get('id'): known[e.tag].add(e.get('id'))
errors, definitions, labtrees = [], {}, []
for file in data.rglob('*.xml'):
    if file.name=='lab_item_colors.xml': continue
    tree=ET.parse(file)
    labtrees.append((file, tree))
    for e in tree.getroot():
        if e.tag in known and e.get('id'):
            key=(e.tag,e.get('id'))
            if key in definitions: errors.append(f'duplicate definition {key}')
            if e.get('id') in known[e.tag]: errors.append(f'overrides vanilla {key}')
            definitions[key]=str(file)
for tag,id in definitions: known[tag].add(id)
known['Item'] |= known['CraftedItem']
for file,tree in labtrees:
    for e in tree.getroot().iter():
        refs=[]
        if e.tag=='CraftedItem': refs.append(('CraftingTemplate',e.get('crafting_template')))
        if e.tag in ['Item','CraftedItem'] and e.get('id','').startswith('cilab_'):
            original_id=e.get('id')[6:]
            if not e.get('name','').startswith('[') or '['+original_id+']' not in e.get('name',''):
                errors.append(f'{file.name}: missing searchable item labels {original_id}')
        if e.tag in ['Piece','AvailablePiece']: refs.append(('CraftingPiece',e.get('id')))
        if e.tag=='UsablePiece': refs.append(('CraftingPiece',e.get('piece_id')))
        if e.tag=='WeaponDescription' and len(e)==0: refs.append(('WeaponDescription',e.get('id')))
        if e.get('weapon_description'): refs.append(('WeaponDescription',e.get('weapon_description')))
        for attr,val in e.attrib.items():
            for prefix in ['Culture','Monster','Item']:
                if val.startswith(prefix+'.'): refs.append((prefix,val[len(prefix)+1:]))
        for tag,id in refs:
            if id and id not in known[tag]: errors.append(f'{file.name}: missing {tag} {id}')
arena_names=['arena_'+culture+'_a' for culture in ['empire','vlandia','battania','sturgia','aserai','khuzait']]
for scene in arena_names:
    if not (game/'Modules'/'SandBox'/'SceneObj'/scene).is_dir(): errors.append(f'missing arena scene {scene}')
report={'items':sum(tag in ['Item','CraftedItem'] for tag,id in definitions),
        'definition_counts':dict(Counter(tag for tag,id in definitions)),
        'arena_scenes':arena_names,
        'errors':sorted(set(errors)), 'runtime_gameplay_verified':False}
(root/'docs'/'validation-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
