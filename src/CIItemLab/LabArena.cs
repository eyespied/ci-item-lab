using System;
using System.Linq;
using Path = System.IO.Path;
using System.Xml.Linq;
using System.Globalization;
using TaleWorlds.CampaignSystem;
using TaleWorlds.CampaignSystem.AgentOrigins;
using TaleWorlds.Core;
using TaleWorlds.Engine;
using TaleWorlds.Library;
using TaleWorlds.MountAndBlade;
using TaleWorlds.MountAndBlade.Source.Missions;
using TaleWorlds.MountAndBlade.Source.Missions.Handlers;
using TaleWorlds.MountAndBlade.View;
using TaleWorlds.MountAndBlade.View.MissionViews;
using TaleWorlds.ObjectSystem;

namespace CIItemLab
{
    internal static class LabArena
    {
        public static void Open(string scene, int mode)
        {
            var rec = new MissionInitializerRecord(scene) { PlayingInCampaignMode = false, DecalAtlasGroup = 3 };
            MissionState.OpenNew("CIItemLabArena", rec, mission => new MissionBehavior[]
            {
                new LabArenaLogic(mode, scene),
                new MissionOptionsComponent(),
                new AgentHumanAILogic(),
                new MissionFacialAnimationHandler(),
                new MissionAgentPanicHandler()
            });
        }
    }

    [ViewCreatorModule]
    public static class LabArenaViews
    {
        [ViewMethod("CIItemLabArena")]
        public static MissionView[] Create(Mission mission) => new[]
        {
            ViewCreator.CreateMissionSingleplayerEscapeMenu(false),
            ViewCreator.CreateOptionsUIHandler(),
            ViewCreator.CreateMissionLeaveView(),
            ViewCreator.CreateMissionAgentStatusUIHandler(mission),
            ViewCreator.CreateMissionMainAgentEquipmentController(mission),
            ViewCreator.CreateMissionMainAgentEquipDropView(mission),
            ViewCreator.CreatePhotoModeView()
        };
    }

    public sealed class LabArenaLogic : MissionLogic, IAgentStateDecider
    {
        private readonly int _mode;
        private readonly string _scene;
        private bool _finished;
        public LabArenaLogic(int mode, string scene) { _mode = mode; _scene = scene; }

        public override void AfterStart()
        {
            base.AfterStart();
            try
            {
                var frames = Mission.Scene.FindEntitiesWithTag(_mode == 3 ? "spawnpoint_player" : "sp_arena")
                    .Select(e => e.GetGlobalFrame()).ToList();
                if (_mode == 3 && frames.Count == 0)
                {
                    // Editor-only prefab entities can be omitted from the live scene.
                    // Use the authored player marker's coordinates in that case.
                    var gameRoot = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(typeof(Mission).Assembly.Location), "..", ".."));
                    var sceneFile = Path.Combine(gameRoot, "Modules", "SandBox", "SceneObj", _scene, "scene.xscene");
                    var marker = XDocument.Load(sceneFile).Descendants("game_entity")
                        .FirstOrDefault(e => (string)e.Attribute("prefab") == "sp_player");
                    var coords = ((string)marker?.Element("transform")?.Attribute("position"))?.Split(',');
                    if (coords != null && coords.Length == 3)
                        frames.Add(new MatrixFrame(Mat3.Identity, new Vec3(
                            float.Parse(coords[0], CultureInfo.InvariantCulture),
                            float.Parse(coords[1], CultureInfo.InvariantCulture),
                            float.Parse(coords[2], CultureInfo.InvariantCulture))));
                }
                if (frames.Count < (_mode == 3 ? 1 : 2))
                    throw new InvalidOperationException("This scene has no usable player spawn points.");
                var playerFrame = frames[0];
                var enemyFrame = frames.OrderByDescending(f => (f.origin - playerFrame.origin).LengthSquared).First();
                Mission.Teams.Add(BattleSideEnum.Defender, 0xff4a100c, 0xffa88220, null);
                Mission.Teams.Add(BattleSideEnum.Attacker, 0xff17365d, 0xffdddddd, null);
                Mission.PlayerTeam = Mission.Teams.Defender;
                Mission.SetMissionMode(MissionMode.Battle, true);
                Spawn(CharacterObject.PlayerCharacter, playerFrame, Mission.PlayerTeam, true);
                if (_mode == 1 || _mode == 2)
                {
                    var opponent = MBObjectManager.Instance.GetObject<CharacterObject>(_mode == 2 ? "vlandian_champion" : "imperial_recruit")
                        ?? MBObjectManager.Instance.GetObject<CharacterObject>("imperial_recruit");
                    if (opponent == null) throw new InvalidOperationException("No sparring troop found.");
                    Spawn(opponent, enemyFrame, Mission.PlayerEnemyTeam, false);
                }
                InformationManager.DisplayMessage(new InformationMessage("CI test scene: F8 catalog | F9 restart | F10 return to map. Photo mode is available from the escape menu."));
            }
            catch (Exception ex)
            {
                InformationManager.DisplayMessage(new InformationMessage("CI arena: " + ex.Message + " Press F10 to return."));
            }
        }

        private Agent Spawn(CharacterObject character, MatrixFrame frame, Team team, bool player)
        {
            frame.rotation.OrthonormalizeAccordingToForwardAndKeepUpAsZAxis();
            var position = frame.origin;
            var direction = frame.rotation.f.AsVec2.Normalized();
            var equipment = new Equipment(character.FirstBattleEquipment);
            var data = new AgentBuildData(character).Team(team).InitialPosition(in position).InitialDirection(in direction)
                .Equipment(equipment).NoHorses(_mode == 1 || _mode == 3).BodyProperties(character.GetBodyPropertiesMax())
                .TroopOrigin(new LabAgentOrigin(character)).Controller(player ? AgentControllerType.Player : AgentControllerType.AI);
            var palette = ItemColors.PaletteFor(equipment);
            if (palette != null) data.ClothingColor1(palette[0]).ClothingColor2(palette[1]);
            var agent = Mission.SpawnAgent(data);
            agent.Health = agent.HealthLimit = agent.BaseHealthLimit = 100;
            agent.FadeIn();
            if (player) Mission.MainAgent = agent;
            else agent.SetWatchState(Agent.WatchState.Alarmed);
            return agent;
        }

        public AgentState GetAgentState(Agent agent, float deathProbability, out bool usedSurgery)
        { usedSurgery = false; return AgentState.Unconscious; }

        public override void OnAgentRemoved(Agent affectedAgent, Agent affectorAgent, AgentState agentState, KillingBlow killingBlow)
        {
            if (!affectedAgent.IsHuman || _finished) return;
            _finished = true;
            InformationManager.DisplayMessage(new InformationMessage("Round finished. F9 to restart, F8 to change gear, F10 to leave."));
        }

        public override InquiryData OnEndMissionRequest(out bool canPlayerLeave)
        { canPlayerLeave = true; return null; }
    }

    // Keep test-agent callbacks from changing campaign health, deaths, rosters or XP.
    internal sealed class LabAgentOrigin : IAgentOriginBase
    {
        private readonly IAgentOriginBase _appearance;
        public LabAgentOrigin(CharacterObject troop) { _appearance = new SimpleAgentOrigin(troop); }
        public bool IsUnderPlayersCommand => _appearance.IsUnderPlayersCommand;
        public bool IsInSameArmyAsPlayer => false;
        public uint FactionColor => _appearance.FactionColor;
        public uint FactionColor2 => _appearance.FactionColor2;
        public IBattleCombatant BattleCombatant => null;
        public int UniqueSeed => _appearance.UniqueSeed;
        public int Seed => _appearance.Seed;
        public Banner Banner => _appearance.Banner;
        public BasicCharacterObject Troop => _appearance.Troop;
        public bool HasThrownWeapon => _appearance.HasThrownWeapon;
        public bool HasHeavyArmor => _appearance.HasHeavyArmor;
        public bool HasShield => _appearance.HasShield;
        public bool HasSpear => _appearance.HasSpear;
        public void SetWounded() { }
        public void SetKilled() { }
        public void SetRouted(bool isOrderRetreat) { }
        public void OnAgentRemoved(float agentHealth) { }
        public void OnScoreHit(BasicCharacterObject victim, BasicCharacterObject formationCaptain, int damage, bool isFatal, bool isTeamKill, WeaponComponentData attackerWeapon) { }
        public void SetBanner(Banner banner) => _appearance.SetBanner(banner);
        public TroopTraitsMask GetTraitsMask() => _appearance.GetTraitsMask();
    }
}
