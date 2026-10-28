#!/usr/bin/env python3
"""Exercise the bridge's selection and withdrawal logic with small Core stubs."""
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] / 'src/MultiBotBridge.cpp').read_text()


def function(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    while ';' in source[start:opening]:
        start = source.index(signature, start + len(signature))
        opening = source.index('{', start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise ValueError(signature)


prefix = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
#include <list>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>
using uint8 = uint8_t; using uint16 = uint16_t; using uint32 = uint32_t;
using int32 = int32_t; using int64 = int64_t;
using ObjectGuid = uint32;
struct Group { struct MemberSlot { ObjectGuid guid; }; std::list<MemberSlot> slots;
    auto const& GetMemberSlots() const { return slots; } };
enum QuestStatus { QUEST_STATUS_COMPLETE = 1, QUEST_STATUS_INCOMPLETE = 2, QUEST_STATUS_FAILED = 3 };
constexpr uint16 MAX_QUEST_LOG_SIZE = 2;
struct Player { ObjectGuid guid; std::string name; Group* group = nullptr; bool inWorld = true;
    std::array<uint32, MAX_QUEST_LOG_SIZE> quests = {}; QuestStatus status = QUEST_STATUS_INCOMPLETE;
    ObjectGuid GetGUID() const { return guid; } std::string const& GetName() const { return name; }
    Group* GetGroup() const { return group; } bool IsInWorld() const { return inWorld; }
    uint32 GetQuestSlotQuestId(uint16 slot) const { return quests[slot]; }
    QuestStatus GetQuestStatus(uint32) const { return status; } };
using SkillType = uint32;
struct PlayerbotAI { Player* master = nullptr; std::set<uint32> skills; Player* GetMaster() { return master; }
    bool HasSkill(SkillType skill) { return skills.count(skill); } };
using PlayerBotMap = std::map<ObjectGuid, Player*>;
struct Holder { PlayerBotMap bots; int scans = 0;
    auto GetPlayerBotsBegin() { ++scans; return bots.cbegin(); }
    auto GetPlayerBotsEnd() { return bots.cend(); }
    Player* GetPlayerBot(ObjectGuid guid) { auto i = bots.find(guid); return i == bots.end() ? nullptr : i->second; } };
struct PlayerbotMgr : Holder {};
struct RandomMgr : Holder { std::set<ObjectGuid> random; bool IsRandomBot(Player* p) { return random.count(p->guid); }
    bool IsAddclassBot(Player*) { return false; } } sRandomPlayerbotMgr;
struct Manager { PlayerbotMgr* mgr = nullptr; std::map<ObjectGuid, PlayerbotAI*> ais;
    PlayerbotMgr* GetPlayerbotMgr(Player*) { return mgr; }
    PlayerbotAI* GetPlayerbotAI(Player* p) { auto i = ais.find(p->guid); return i == ais.end() ? nullptr : i->second; }
} sPlayerbotsMgr;
struct Cache { std::map<std::string, ObjectGuid> names;
    ObjectGuid GetCharacterGuidByName(std::string const& name) { auto i = names.find(name); return i == names.end() ? 0 : i->second; }
} cache, *sCharacterCache = &cache;
std::string Trim(std::string const& s) { return s; }
constexpr uint32 GUILD_BANK_RIGHT_VIEW_TAB = 1;
constexpr uint32 GUILD_WITHDRAW_SLOT_UNLIMITED = 0xffffffff;
constexpr uint8 GR_GUILDMASTER = 0;
constexpr uint8 GUILD_BANK_MAX_TABS = 6;
struct Guild { struct Member { uint8 rank; int32 used;
        bool IsRank(uint8 r) const { return rank == r; } uint8 GetRankId() const { return rank; }
        int32 GetBankWithdrawValue(uint8) const { return used; } };
    std::map<ObjectGuid, Member> members; ObjectGuid leader = 0;
    Member const* GetMember(ObjectGuid id) const { auto i = members.find(id); return i == members.end() ? nullptr : &i->second; }
    ObjectGuid GetLeaderGUID() const { return leader; } };
using GuildBankRights = std::map<std::pair<uint8, uint8>, std::pair<uint32, uint32>>;
struct QuestEntryData { uint32 questId; bool completed; };
void AppendQuestEntry(std::vector<QuestEntryData>& entries, std::set<uint32>& seen, uint32 id, bool completed, std::string const& mode) {
    if ((mode == "ALL" || (mode == "COMPLETED") == completed) && seen.insert(id).second)
        entries.push_back({id, completed});
}
void SortQuestEntries(std::vector<QuestEntryData>&) {}
struct Field { template<class T> T Get() { return 0; } };
struct Result { Field* Fetch() { static Field fields[2]; return fields; } bool NextRow() { return false; } };
using QueryResult = Result*;
struct Db { int calls = 0; QueryResult Query(char const*, ObjectGuid) { ++calls; return nullptr; } } CharacterDatabase;
struct WorldDb { bool fail = false; Result row; std::string query;
    template<class... T> QueryResult Query(char const* text, T...) {
        query = text; return fail ? nullptr : &row;
    }
} WorldDatabase;
using BridgeReferenceLootRows = std::map<uint32, std::vector<std::pair<uint32, uint32>>>;
std::optional<std::map<uint32, std::set<uint32>>> craftOutputs;
auto const& GetBridgeCraftOutputsBySkill() { return craftOutputs; }
std::array<SkillType, 2> GetBridgeCraftProtectionSkills() { return {1, 2}; }
'''

functions = '\n'.join(function(sig) for sig in [
    'bool IsBotInRequesterGroup(',
    'bool IsBotMasteredByRequester(',
    'bool CanExposeRandomHolderBot(',
    'void AppendBridgeVisibleBot(',
    'std::vector<Player*> GetBridgeVisibleBots(Player* player, bool groupOnly)\n',
    'Player* FindBotByName(Player* player, std::string const& botName)\n',
    'std::vector<Player*> GetBridgeVisibleBotsForScope(Player* player, std::string const& scope, std::string const& target)\n',
    'int32 GetGuildBankTabWithdrawRemaining(',
    'int32 GetEffectiveGuildBankWithdrawRemaining(',
    'std::vector<QuestEntryData> BuildQuestEntries(',
    'bool BuildBridgeCraftProtectedItemIds(',
    'std::optional<BridgeReferenceLootRows> BuildBridgeReferenceLootRows(',
    'std::optional<BridgeReferenceLootRows> BuildBridgeLootTableRows(',
    'void AddBridgeReferenceLootOutputs(',
    'bool AddBridgeLootTableOutputs(',
]).replace('bot->GetGUID().GetCounter()', 'bot->GetGUID()')

checks = r'''
int main() {
    Group group; group.slots = {{3}, {2}, {1}, {4}};
    Group other;
    Player requester{1, "Owner", &group}, owned{2, "Owned", &group};
    Player random{3, "Random", &group}, mastered{4, "Mastered", &other};
    Player human{5, "Human", &group}, hidden{6, "Hidden", &other};
    PlayerbotMgr mgr; mgr.bots = {{2, &owned}}; sPlayerbotsMgr.mgr = &mgr;
    PlayerbotAI randomAI, masteredAI{&requester, {}}, hiddenAI;
    sPlayerbotsMgr.ais = {{3, &randomAI}, {4, &masteredAI}, {6, &hiddenAI}};
    sRandomPlayerbotMgr.bots = {{2, &owned}, {3, &random}, {4, &mastered}, {5, &human}, {6, &hidden}};
    sPlayerbotsMgr.ais[2] = &randomAI;
    sRandomPlayerbotMgr.random = {2, 3, 4, 6};
    cache.names = {{"Owned", 2}, {"Random", 3}, {"Mastered", 4}, {"Human", 5}, {"Hidden", 6}};
    auto grouped = GetBridgeVisibleBots(&requester, true);
    assert((grouped == std::vector<Player*>{&owned, &random}));
    assert(sRandomPlayerbotMgr.scans == 0);
    auto all = GetBridgeVisibleBots(&requester, false);
    assert((all == std::vector<Player*>{&owned, &random, &mastered}));
    assert(FindBotByName(&requester, "Owned") == &owned);
    assert(FindBotByName(&requester, "Random") == &random);
    assert(FindBotByName(&requester, "Mastered") == &mastered);
    assert(FindBotByName(&requester, "Human") == nullptr);
    assert(FindBotByName(&requester, "Hidden") == nullptr);
    random.inWorld = false; assert(FindBotByName(&requester, "Random") == nullptr);
    assert(GetBridgeVisibleBotsForScope(&requester, "BOT", "Mastered").size() == 1);
    requester.group = nullptr; assert(GetBridgeVisibleBots(&requester, true).empty());

    Guild guild; guild.members = {{1, {1, 2}}, {2, {2, 0}}, {3, {0, 0}}};
    GuildBankRights rights = {{{1, 0}, {1, 3}}, {{2, 0}, {0, 10}}, {{1, 1}, {1, GUILD_WITHDRAW_SLOT_UNLIMITED}}};
    assert(GetGuildBankTabWithdrawRemaining(&guild, &requester, 0, rights) == 1);
    guild.members[1].used = 3;
    assert(GetGuildBankTabWithdrawRemaining(&guild, &requester, 0, rights) == 0);
    assert(GetGuildBankTabWithdrawRemaining(&guild, &owned, 0, rights) == 0);
    assert(GetEffectiveGuildBankWithdrawRemaining(&guild, &requester, &owned, rights) == 0);
    assert(GetGuildBankTabWithdrawRemaining(&guild, &requester, 1, rights) == std::numeric_limits<int32>::max());
    assert(GetGuildBankTabWithdrawRemaining(&guild, &random, 0, rights) == std::numeric_limits<int32>::max());
    assert(GetGuildBankTabWithdrawRemaining(&guild, &hidden, 0, rights) == 0);

    owned.quests[0] = 10;
    assert(BuildQuestEntries(&owned, "COMPLETED").empty());
    assert(CharacterDatabase.calls == 0);
    assert(BuildQuestEntries(&owned, "INCOMPLETED").size() == 1);
    owned.quests[0] = 0; BuildQuestEntries(&owned, "ALL");
    assert(CharacterDatabase.calls == 1);

    std::set<uint32> protectedItems;
    randomAI.skills = {1};
    assert(!BuildBridgeCraftProtectedItemIds(&randomAI, protectedItems));
    craftOutputs = std::map<uint32, std::set<uint32>>{{1, {42}}, {2, {99}}};
    assert(BuildBridgeCraftProtectedItemIds(&randomAI, protectedItems));
    assert((protectedItems == std::set<uint32>{42}));
    assert(BuildBridgeReferenceLootRows()->empty());
    assert(WorldDatabase.query.find("UNION ALL SELECT 0, 0, 0") != std::string::npos);
    assert(BuildBridgeLootTableRows("spell_loot_template")->empty());
    std::set<uint32> lootItems;
    assert(AddBridgeLootTableOutputs("milling_loot_template", {}, lootItems));
    WorldDatabase.fail = true;
    assert(!BuildBridgeReferenceLootRows());
    assert(!BuildBridgeLootTableRows("spell_loot_template"));
    assert(!AddBridgeLootTableOutputs("milling_loot_template", {}, lootItems));
}
'''

with tempfile.TemporaryDirectory() as temp:
    cpp = Path(temp) / 'performance_paths.cpp'
    executable = Path(temp) / 'performance_paths'
    cpp.write_text(prefix + functions + checks)
    subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
print('Bridge selection, guild withdrawal, quest and craft protection checks passed')
