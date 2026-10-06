using System.Text.Json;
using TpacTool.Lib;
var result = new List<object>();
foreach(var file in Directory.GetFiles(args[0], "*.tpac", SearchOption.AllDirectories))
{
    Console.WriteLine("Indexing " + Path.GetFileName(file));
    var package = new AssetPackage(file);
    foreach(var mesh in package.Items.OfType<Metamesh>())
        result.Add(new { name=mesh.Name, package=Path.GetFileName(file), slot=mesh.UnknownString,
            cloth=mesh.ClothString, flags=mesh.Meshes.SelectMany(m=>m.MaterialFlags).Distinct().ToArray(),
            parts=mesh.Meshes.Where(m=>m.Lod==0).Select(m=>new {name=m.Name, skin=m.SkinDataSize,
                factor=new[]{m.FactorColor.X,m.FactorColor.Y,m.FactorColor.Z,m.FactorColor.W},
                factor2=new[]{m.Factor2Color.X,m.Factor2Color.Y,m.Factor2Color.Z,m.Factor2Color.W}}).ToArray() });
}
File.WriteAllText(args[1],JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine("Indexed " + result.Count + " mesh assets");
