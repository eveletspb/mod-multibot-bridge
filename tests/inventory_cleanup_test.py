#!/usr/bin/env python3
"""Exercise shipped cleanup policy and batch execution without touching a live inventory."""
from pathlib import Path
import subprocess
import tempfile

playerbots = Path(__file__).resolve().parents[2] / "mod-playerbots"
usage_source = (playerbots / "src/Ai/Base/Value/ItemUsageValue.cpp").read_text()

source = (Path(__file__).resolve().parents[1] / 'src/MultiBotBridge.cpp').read_text()

def function(signature, text=source):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 0
    for pos in range(opening, len(text)):
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise ValueError(signature)

prefix = r'''
#include <array>
#include <cstdlib>
#include <cctype>
#include <limits>
#include <cassert>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <sstream>
#include <vector>
using uint8 = uint8_t; using uint32 = uint32_t; using int32 = int32_t; using uint64 = uint64_t;
struct ObjectGuid {uint32 value=0; ObjectGuid(uint32 v=0):value(v){} operator uint32()const{return value;}
 bool IsItem()const{return false;}};
using ItemUsage = int;
using ChatMsg = int;
constexpr char kFieldSeparator = '~';
constexpr uint32 kMaxStateBots = 128;
constexpr uint8 INVENTORY_SLOT_BAG_0=255, INVENTORY_SLOT_ITEM_START=23, INVENTORY_SLOT_ITEM_END=39,
 INVENTORY_SLOT_BAG_START=19, INVENTORY_SLOT_BAG_END=23, MAX_QUEST_LOG_SIZE=3;
enum { ITEM_CLASS_ARMOR, ITEM_CLASS_QUEST, ITEM_CLASS_KEY, ITEM_CLASS_PROJECTILE, ITEM_CLASS_REAGENT,
 ITEM_CLASS_MISC, ITEM_CLASS_CONSUMABLE, ITEM_CLASS_TRADE_GOODS, ITEM_CLASS_WEAPON, ITEM_CLASS_RECIPE };
enum { ITEM_SUBCLASS_JUNK=0, ITEM_SUBCLASS_CONSUMABLE=0, ITEM_SUBCLASS_POTION=1, ITEM_SUBCLASS_ELIXIR=2,
 ITEM_SUBCLASS_FLASK=3, ITEM_SUBCLASS_SCROLL=4, ITEM_SUBCLASS_FOOD=5, ITEM_SUBCLASS_ITEM_ENHANCEMENT=6,
 ITEM_SUBCLASS_BANDAGE=7, ITEM_SUBCLASS_CONSUMABLE_OTHER=8 };
enum { ITEM_USAGE_NONE, ITEM_USAGE_VENDOR, ITEM_USAGE_AH, ITEM_USAGE_DISENCHANT, ITEM_USAGE_EQUIP,
 ITEM_USAGE_REPLACE, ITEM_USAGE_BROKEN_EQUIP, ITEM_USAGE_QUEST, ITEM_USAGE_SKILL, ITEM_USAGE_USE,
 ITEM_USAGE_GUILD_TASK, ITEM_USAGE_KEEP, ITEM_USAGE_AMMO, ITEM_USAGE_BAD_EQUIP };
enum { ITEM_QUALITY_LEGENDARY=5, ITEM_FLAG_NO_USER_DESTROY=1, EQUIP_ERR_OK=0,
 SPELL_EFFECT_CREATE_ITEM=24, SPELL_EFFECT_CREATE_ITEM_2=25, UNIT_NPC_FLAG_VENDOR=128,
 CREATURE_FLAG_EXTRA_NO_SELL_VENDOR=1, CMSG_SELL_ITEM=1, CMSG_DESTROYITEM=2 };
constexpr uint32 BIND_QUEST_ITEM=4, BIND_WHEN_PICKED_UP=1, BIND_WHEN_EQUIPPED=2, SKILL_ENCHANTING=333,
 POWER_MANA=0, ITEM_QUALITY_UNCOMMON=2, ITEM_QUALITY_NORMAL=1, MAX_ITEM_PROTO_SPELLS=5,
 QUEST_ITEM_OBJECTIVES_COUNT=6, EQUIPMENT_SLOT_MAINHAND=15, EQUIPMENT_SLOT_OFFHAND=16,
 SPELL_EFFECT_ENERGIZE=30, SPELL_EFFECT_HEAL=10,
 ITEM_SUBCLASS_WEAPON_MISC=14, ITEM_SUBCLASS_WEAPON_FISHING_POLE=20;
struct ItemTemplate {
 uint32 ItemId=1, Class=ITEM_CLASS_TRADE_GOODS, SubClass=0, Quality=1, StartQuest=0, SellPrice=1, MaxCount=0, Bonding=0, RequiredDisenchantSkill=0, TotemCategory=0; std::string Name1;
 bool protectedFlag=false;
 struct Spell {uint32 SpellId=0,SpellCategory=0;}; std::array<Spell,5> Spells{};
 bool HasFlag(int)const{return protectedFlag;}
};
struct Quest {uint32 src=0; std::array<uint32,4> ItemDrop{}; std::array<uint32,6> RequiredItemId{},RequiredItemCount{};
 uint32 GetSrcItemId()const{return src;}};
struct ObjectManager {std::map<uint32,Quest> quests;std::map<uint32,ItemTemplate const*> templates;
 ItemTemplate const* GetItemTemplate(uint32 id){auto it=templates.find(id);return it==templates.end()?nullptr:it->second;}
 Quest const* GetQuestTemplate(uint32 id){auto it=quests.find(id);return it==quests.end()?nullptr:&it->second;}
} objects, *sObjectMgr=&objects;
struct SpellInfo {struct Effect {uint32 Effect=0,ItemType=0;};std::array<Effect,3> Effects{};};
struct SpellManager {std::map<uint32,SpellInfo> spells;
 SpellInfo const* GetSpellInfo(uint32 id){auto it=spells.find(id);return it==spells.end()?nullptr:&it->second;}
} spells, *sSpellMgr=&spells;
struct Item {
 ObjectGuid guid=1,owner=2; uint8 bag=255,slot=23; uint32 count=1; int suffix=-42, usage=ITEM_USAGE_VENDOR;
 bool trade=false, refund=false, bop=false, wrapped=false, nonempty=false;
 ItemTemplate proto;
 ObjectGuid GetGUID()const{return guid;} ObjectGuid GetOwnerGUID()const{return owner;}
 bool IsSoulBound()const{return false;} bool IsInTrade()const{return trade;} bool IsRefundable()const{return refund;} bool IsBOPTradable()const{return bop;}
 bool IsWrapped()const{return wrapped;} bool IsNotEmptyBag()const{return nonempty;}
 uint8 GetBagSlot()const{return bag;} uint8 GetSlot()const{return slot;}
 uint32 GetEntry()const{return proto.ItemId;} uint32 GetCount()const{return count;}
 ItemTemplate const* GetTemplate()const{return &proto;} int GetItemRandomPropertyId()const{return suffix;}
};
struct Bag {std::vector<Item*> items; uint32 GetBagSize()const{return items.size();}
 Item* GetItemByPos(uint32 slot){return items[slot];}};
struct Creature {ObjectGuid guid=99;bool noSell=false;
 ObjectGuid GetGUID()const{return guid;} bool HasFlagsExtra(int)const{return noSell;}} vendor;
struct WorldPacket {
 std::vector<uint32> data; WorldPacket(int,int=0){}
 template<class T> WorldPacket& operator<<(T v){data.push_back(v);return *this;}
};
namespace WorldPackets::Item {
struct SellItem {WorldPacket packet; SellItem(WorldPacket&& p):packet(std::move(p)){} void Read(){}};
struct DestroyItem {WorldPacket packet; DestroyItem(WorldPacket&& p):packet(std::move(p)){} void Read(){}};
}
struct Player;
struct Session {Player* bot=nullptr; int sales=0,destroys=0; bool veto=false;
 void HandleSellItemOpcode(WorldPackets::Item::SellItem&);
 void HandleDestroyItemOpcode(WorldPackets::Item::DestroyItem&);
};
struct Context {
 std::vector<std::string> outfits;
 template<class T> struct Value {std::vector<std::string>& outfits; T Get(){return outfits;}};
 Value<std::vector<std::string>&> value{outfits};
 template<class T> Value<T>* GetValue(char const*){return &value;}
};
struct PlayerbotAI {Context values; Player* bot=nullptr;bool context=true,gold=false;
 Player* GetMaster(){return bot;} bool HasSkill(int){return false;}
 std::map<Quest const*,uint32> GetCurrentQuestsRequiringItemId(uint32){return {};}
 Item* FindStoneFor(Item*){return nullptr;} Item* FindOilFor(Item*){return nullptr;}
 Context* GetAiObjectContext(){return context?&values:nullptr;} bool HasCheat(int){return gold;}};
namespace BotCheatMask {constexpr int gold=1;}
struct Player {
 ObjectGuid guid=2,loot=0; std::string name="Bot"; bool available=true,world=true,alive=true,combat=false,
 nearby=true,trade=false,casting=false,interact=true,allowed=true; uint32 money=10;
 Session session{this}; PlayerbotAI ai{{},this}; std::array<uint32,3> quests{};
 std::map<uint32,Item*> items; Bag* bag=nullptr; bool needsQuest=false,rewarded=false;
 bool HasSpell(uint32){return false;} uint32 GetPower(int){return 0;} uint32 GetGuildId(){return 0;}
 uint32 GetSkillValue(int){return 0;}
 Item* GetItemByEntry(uint32 entry){for(auto [_,i]:items)if(i->proto.ItemId==entry)return i;return nullptr;}
 uint32 GetItemCount(uint32 entry,bool){uint32 n=0;for(auto [_,i]:items)if(i->proto.ItemId==entry)n+=i->count;return n;}
 ObjectGuid GetGUID()const{return guid;} ObjectGuid GetLootGUID()const{return loot;}
 bool HasQuestForItem(uint32)const{return needsQuest;} uint32 GetQuestSlotQuestId(uint8 s){return quests[s];}
 bool GetQuestRewardStatus(uint32)const{return rewarded;} int CanUseItem(ItemTemplate const*)const{return 0;}
 Item* GetItemByGuid(ObjectGuid g){auto it=items.find(g);return it==items.end()?nullptr:it->second;}
 Item* GetItemByPos(uint8 b,uint32 s){for(auto [_,i]:items)if(i->bag==b&&i->slot==s)return i;return nullptr;}
 Bag* GetBagByPos(uint8 b){return b==19?bag:nullptr;}
 Session* GetSession(){return available?&session:nullptr;} bool IsInWorld(){return world;} bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;} bool IsWithinDistInMap(Player* p,float d){assert(d==30);return p->nearby;}
 void* GetTradeData(){return trade?this:nullptr;} bool IsNonMeleeSpellCast(bool){return casting;}
 Creature* GetNPCIfCanInteractWith(ObjectGuid,int){return interact?&vendor:nullptr;}
 uint32 GetMoney(){return money;} void SetMoney(uint32 v){money=v;} std::string GetName(){return name;}
};
void Session::HandleSellItemOpcode(WorldPackets::Item::SellItem& p){++sales;if(!veto){bot->items.erase(p.packet.data[1]);bot->money+=5;}}
void Session::HandleDestroyItemOpcode(WorldPackets::Item::DestroyItem& p){++destroys;
 auto* i=bot->GetItemByPos(p.packet.data[0],p.packet.data[1]);assert(i);bot->items.erase(i->guid);}
PlayerbotAI* GetBotAI(Player* p){return &p->ai;}
bool CanControlBridgeBot(Player*,Player* p){return p->allowed;}
Creature* FindNearbyInteractiveVendor(Player* p){return p->interact?&vendor:nullptr;}
bool IsRealPlayer(Player*){return true;} bool IsSelfBot(Player*){return false;}
bool IsRoguePoison(ItemTemplate const*){return false;}
struct Config{bool SyncQuestWithPlayer=true;} sPlayerbotAIConfig;
struct GuildTaskMgr {static GuildTaskMgr& instance(){static GuildTaskMgr mgr;return mgr;}
 bool IsGuildTaskItem(uint32,uint32){return false;}};
struct LootObject {ObjectGuid guid;};
template<class T>T AIValue(){return {};}
#define AI_VALUE(type,name) AIValue<type>()
#define AI_VALUE2(type,name,qualifier) AIValue<type>()
struct ParsedItemUsage {uint32 itemId=0;int32 randomPropertyId=0;};
// Core equipment/skill decisions are fixtures; Calculate/GetConsumableType/qualifier parsing below are shipped code.
struct ItemUsageValue {
 PlayerbotAI* botAI;Player* bot;std::string qualifier;
 explicit ItemUsageValue(PlayerbotAI* ai):botAI(ai),bot(ai->bot){
  for(auto [_,i]:bot->items)objects.templates[i->GetEntry()]=i->GetTemplate();
 }
 void Qualify(std::string s){qualifier=s;}
 ParsedItemUsage GetItemIdFromQualifier();
 bool IsItemUsefulForSkill(ItemTemplate const*){return false;}
 bool IsItemNeededForSkill(ItemTemplate const*){return false;}
 bool IsItemNeededForClassSpell(ItemTemplate const*){return false;}
 bool IsItemNeededForUsefullSpell(ItemTemplate const*,bool){return false;}
 bool IsStartQuestItemUsefulFor(Player*,ItemTemplate const*){return false;}
 ItemUsage QueryItemUsageForEquip(ItemTemplate const* proto,int32 suffix){
  auto* item=bot->GetItemByEntry(proto->ItemId);assert(item&&item->suffix==suffix);return item->usage;
 }
 bool IsItemUsefulForQuest(Player*,ItemTemplate const*){return false;}
 ItemUsage QueryItemUsageForAmmo(ItemTemplate const*){return ITEM_USAGE_NONE;}
 bool IsTemporaryWeaponEnchantment(ItemTemplate const*){return false;}
 bool IsBestPoison(ItemTemplate const*){return false;}
 float CurrentStacks(ItemTemplate const*){return 0;}
 float BetterStacks(ItemTemplate const*,std::string const&){return 0;}
 std::string const GetConsumableType(ItemTemplate const*,bool);
 ItemUsage Calculate();
};
std::vector<Player*> visibleBots;
auto GetBridgeVisibleBots(Player*){return visibleBots;}
bool rate=true,heavy=true,fresh=true;
bool ConsumeItemActionRateLimit(Player*){return rate;}
bool ConsumeSelfBotHeavyActionRateLimit(Player*){return heavy;}
bool RegisterItemActionToken(Player*,std::string const&){return fresh;}
std::string UrlEncodeField(std::string const& s){return s;}
std::string Trim(std::string const& value){auto start=value.find_first_not_of(" ");return start==std::string::npos?"":value.substr(start,value.find_last_not_of(" ")-start+1);}
std::vector<std::pair<std::string,std::string>> packets;
bool SendStateAddonPacket(Player*,ChatMsg,std::string op,std::string payload){packets.push_back({op,payload});return true;}
#define LOG_INFO(...) (void)0
'''
checks = r'''
int main(){
 Player owner; owner.guid=1;
 Player bot; Item oldGear; bot.items[1]=&oldGear;
 assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 for(int usage:{ITEM_USAGE_EQUIP,ITEM_USAGE_REPLACE,ITEM_USAGE_BROKEN_EQUIP,ITEM_USAGE_QUEST,
 ITEM_USAGE_SKILL,ITEM_USAGE_USE,ITEM_USAGE_GUILD_TASK,ITEM_USAGE_KEEP,ITEM_USAGE_AMMO}){
  oldGear.usage=usage;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 }
 for(int usage:{ITEM_USAGE_NONE,ITEM_USAGE_VENDOR,ITEM_USAGE_AH,ITEM_USAGE_DISENCHANT}){
  oldGear.usage=usage;assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 }
 oldGear.slot=15;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 oldGear.slot=40;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));oldGear.slot=23;
 for(bool* flag:{&oldGear.trade,&oldGear.refund,&oldGear.bop,&oldGear.wrapped,&oldGear.nonempty,&oldGear.proto.protectedFlag}){
  *flag=true;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));*flag=false;
 }
 for(auto cls:{ITEM_CLASS_KEY,ITEM_CLASS_PROJECTILE,ITEM_CLASS_REAGENT}){
  oldGear.proto.Class=cls;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 }
 oldGear.proto.Class=ITEM_CLASS_CONSUMABLE;oldGear.proto.MaxCount=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));oldGear.proto.MaxCount=0;
 oldGear.proto.Class=ITEM_CLASS_QUEST;oldGear.proto.SellPrice=0;oldGear.usage=ITEM_USAGE_NONE;
 assert(IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{})); // old quest leftover
 bot.quests[0]=50; objects.quests[50].RequiredItemId[0]=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{})); // including exact/completed requirement counts
 objects.quests[50].RequiredItemId[0]=2;oldGear.proto.Class=ITEM_CLASS_TRADE_GOODS;oldGear.proto.Spells[0].SpellId=10;
 spells.spells[10].Effects[0]={SPELL_EFFECT_CREATE_ITEM,2};
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 spells.spells.clear();objects.quests[50].src=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));objects.quests[50].src=0;
 objects.quests[50].ItemDrop[0]=1;assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{}));
 objects.quests[50].ItemDrop[0]=0;objects.quests[50].RequiredItemId[5]=1;
 assert(!IsBridgeCleanupCandidate(&bot,&bot.ai,&oldGear,{})); // sixth objective slot
 objects.quests.clear();bot.quests[0]=0;oldGear.proto.Spells[0].SpellId=0;
 oldGear.proto.Class=ITEM_CLASS_QUEST;
 Item sell=oldGear, keep=oldGear, extra=oldGear;
 oldGear.guid=1;sell.guid=2;sell.slot=24;sell.proto.ItemId=2;sell.proto.SellPrice=1;sell.usage=ITEM_USAGE_AH;
 keep.guid=3;keep.slot=25;keep.proto.ItemId=3;keep.usage=ITEM_USAGE_EQUIP;
 extra.guid=4;extra.bag=19;extra.slot=0;extra.proto.ItemId=4;extra.proto.SellPrice=1;
 Bag bag;bag.items={&extra};bot.bag=&bag;
 bot.items={{1,&oldGear},{2,&sell},{3,&keep},{4,&extra}};
 uint32 sold=0,destroyed=0,failed=0;bot.ai.gold=true;
 CleanupBridgeBagItems(&owner,&bot,&vendor,sold,destroyed,failed);
 assert(sold==2&&destroyed==1&&failed==0&&bot.items.size()==1&&bot.money==10);
 bot.bag=nullptr;bot.items={{2,&sell}};bot.session.veto=true;sold=destroyed=failed=0;
 CleanupBridgeBagItems(&owner,&bot,&vendor,sold,destroyed,failed);
 assert(sold==0&&destroyed==0&&failed==1&&bot.items.size()==1); // no destruction after veto
 bot.session.veto=false;
 Player far, forbidden, fighting, noVendor;
 far.nearby=false;forbidden.allowed=false;fighting.combat=true;noVendor.interact=false;
 visibleBots={&bot,&far,&forbidden,&fighting,&noVendor};
 packets.clear();RunInventoryCleanupCommand(&owner,0,"token");
 assert(packets.back().first=="CLEANUP_END"&&packets.back().second=="token~PARTIAL~PARTIAL~1~4~1~0~0");
 assert(bot.items.empty()&&forbidden.session.sales==0);
 bot.items={{2,&sell}};owner.combat=true;packets.clear();RunInventoryCleanupCommand(&owner,0,"combat");
 assert(bot.items.size()==1&&packets.back().second=="combat~ERR~IN_COMBAT~0~0~0~0~0");owner.combat=false;
 heavy=false;RunInventoryCleanupCommand(&owner,0,"rate");assert(bot.items.size()==1);heavy=true;
 fresh=false;RunInventoryCleanupCommand(&owner,0,"duplicate");assert(bot.items.size()==1);fresh=true;

 // A quest tool can belong to a later chain step with no direct template references.
 Player safeBot;
 Item tool, flask, outfit, fishingPole;
 tool.guid=10;tool.slot=23;tool.proto.ItemId=22115;tool.proto.Class=ITEM_CLASS_QUEST;
 tool.proto.MaxCount=1;tool.proto.SellPrice=0;tool.proto.Spells[0].SpellId=27616;tool.usage=ITEM_USAGE_NONE;
 flask.guid=11;flask.slot=24;flask.proto.ItemId=46376;flask.proto.Class=ITEM_CLASS_CONSUMABLE;
 flask.proto.SubClass=ITEM_SUBCLASS_FLASK;flask.proto.Spells[0].SpellId=53755;
 flask.proto.MaxCount=0;flask.proto.SellPrice=2500;flask.usage=ITEM_USAGE_NONE;
 outfit.guid=12;outfit.slot=25;outfit.proto.ItemId=12345;outfit.proto.Class=ITEM_CLASS_ARMOR;outfit.usage=ITEM_USAGE_NONE;
 safeBot.items={{10,&tool},{11,&flask},{12,&outfit}};
 safeBot.ai.values.outfits={"unused=999", "resistance = 12345,456", "broken", "offspec=777", "bad=9999999999999999999999"};
 // These remain NONE/AH under the real Playerbots classifier; bridge protection must take precedence.
 ItemUsageValue toolUsage(&safeBot.ai);toolUsage.Qualify("22115,-42");
 assert(toolUsage.Calculate()==ITEM_USAGE_NONE);
 spells.spells[53755].Effects[0]={6,0}; // APPLY_AURA: a real buff, not a heal/create effect
 ItemUsageValue flaskUsage(&safeBot.ai);flaskUsage.Qualify("46376,-42");
 assert(flaskUsage.GetConsumableType(&flask.proto,false).empty());
 assert(flaskUsage.Calculate()==ITEM_USAGE_AH);
 ItemUsageValue outfitUsage(&safeBot.ai);outfitUsage.Qualify("12345,-42");
 assert(outfitUsage.Calculate()==ITEM_USAGE_AH);
 Item outfitCopy=outfit;outfitCopy.guid=13;outfitCopy.slot=26;outfitCopy.suffix=77;
 safeBot.items[13]=&outfitCopy;
 fishingPole.guid=15;fishingPole.slot=28;fishingPole.proto.ItemId=19970;fishingPole.proto.Class=ITEM_CLASS_WEAPON;
 fishingPole.proto.SubClass=ITEM_SUBCLASS_WEAPON_FISHING_POLE;fishingPole.proto.Quality=3;
 fishingPole.proto.SellPrice=2175;fishingPole.usage=ITEM_USAGE_NONE;safeBot.items[15]=&fishingPole;
 Item trash;trash.guid=14;trash.slot=27;trash.proto.ItemId=998;trash.proto.Class=ITEM_CLASS_QUEST;
 trash.proto.SellPrice=0;trash.usage=ITEM_USAGE_NONE;
 for(uint32 questId:{8960,9032}){
  safeBot.quests[0]=questId;objects.quests[questId]={};
  safeBot.items[14]=&trash;int const destroysBefore=safeBot.session.destroys;
  visibleBots={&safeBot};packets.clear();RunInventoryCleanupCommand(&owner,0,"safe");
  assert(safeBot.items.size()==5&&safeBot.session.sales==0&&safeBot.session.destroys==destroysBefore+1);
  for(uint32 id:{10,11,12,13,15})assert(safeBot.GetItemByGuid(id));
  assert(packets.back().second=="safe~OK~OK~1~0~0~1~0");
 }
 // Buffs, food, potions, scrolls and enhancements remain safe even if AI marks them AH/NONE.
 for(uint32 cls:{ITEM_SUBCLASS_FLASK,ITEM_SUBCLASS_ELIXIR,ITEM_SUBCLASS_SCROLL,ITEM_SUBCLASS_POTION,
 ITEM_SUBCLASS_FOOD,ITEM_SUBCLASS_CONSUMABLE_OTHER,ITEM_SUBCLASS_ITEM_ENHANCEMENT}){
  flask.proto.SubClass=cls;flask.proto.SellPrice=0;
  assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&flask,{}));
  flask.proto.SellPrice=2500;
  assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&flask,{}));
 }
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&fishingPole,{}));
 fishingPole.proto.SubClass=ITEM_SUBCLASS_WEAPON_MISC;
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&fishingPole,{}));
 fishingPole.proto.Class=ITEM_CLASS_TRADE_GOODS;fishingPole.proto.TotemCategory=1;
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&fishingPole,{}));
 auto const outfitIds=GetBridgeCleanupOutfitItemIds(&safeBot.ai);
 assert(outfitIds==std::set<uint32>({999,12345,456,777}));
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&outfit,outfitIds));
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&outfitCopy,outfitIds));
 safeBot.items.erase(13);
 assert(IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&outfit,{})); // unsaved obsolete gear is still removable
 // Quest tools are kept when their chain is not currently represented in the log, too.
 safeBot.quests[0]=0;
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&tool,{}));
 tool.proto.Class=ITEM_CLASS_ARMOR;tool.proto.Bonding=BIND_QUEST_ITEM;
 assert(!IsBridgeCleanupCandidate(&safeBot,&safeBot.ai,&tool,{})); // quest-bound equipment/tool
 visibleBots.assign(129,&bot);RunInventoryCleanupCommand(&owner,0,"limit");
 assert(bot.items.size()==1&&packets.back().second=="limit~ERR~TOO_MANY_BOTS~0~0~0~0~0");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'cleanup.cpp'
    signatures = ['bool TryParseUint32Field(', 'std::vector<uint32> ParseOutfitItemEntries(', 'bool IsBridgeCleanupQuestItem(',
                  'std::set<uint32> GetBridgeCleanupOutfitItemIds(', 'bool IsBridgeCleanupCandidate(',
                  'void CleanupBridgeBagItems(', 'void RunInventoryCleanupCommand(']
    usage_signatures = ['ParsedItemUsage ItemUsageValue::GetItemIdFromQualifier(',
                        'std::string const ItemUsageValue::GetConsumableType(',
                        'ItemUsage ItemUsageValue::Calculate(']
    path.write_text(prefix + '\n'.join(function(s, usage_source) for s in usage_signatures) +
                    '\n'.join(function(s) for s in signatures) + checks)
    binary = Path(tmp) / 'cleanup'
    subprocess.run(['c++', '-std=c++20', '-fsanitize=address,undefined', '-g', str(path), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Inventory cleanup: real usage classification, quest tools/objectives, buffs, saved outfits, old junk and batch safety passed')
