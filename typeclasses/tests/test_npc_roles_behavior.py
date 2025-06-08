from unittest.mock import MagicMock
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from world.guilds import Guild, save_guild, find_guild
from world.quests import Quest, save_quest
from utils.currency import from_copper, to_copper
from typeclasses.npcs import (
    MerchantNPC,
    BankerNPC,
    TrainerNPC,
    GuildmasterNPC,
    GuildReceptionistNPC,
    QuestGiverNPC,
    EventNPC,
)


class TestNPCRoleBehaviors(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = MagicMock()

    def test_merchant_sell_transfers_item_and_coins(self):
        merchant = create.create_object(MerchantNPC, key="shopkeep", location=self.room1)
        item = create.create_object("typeclasses.objects.Object", key="apple", location=merchant)
        self.char1.db.coins = from_copper(20)
        merchant.db.coins = from_copper(0)

        merchant.sell(self.char1, item, 10)

        self.assertEqual(item.location, self.char1)
        self.assertEqual(to_copper(self.char1.db.coins), 10)
        self.assertEqual(to_copper(merchant.db.coins), 10)

    def test_banker_deposit_and_withdraw(self):
        banker = create.create_object(BankerNPC, key="banker", location=self.room1)
        self.char1.db.coins = from_copper(30)

        banker.deposit(self.char1, 20)
        self.assertEqual(to_copper(self.char1.db.coins), 10)
        self.assertEqual(self.char1.db.bank, 20)

        banker.withdraw(self.char1, 5)
        self.assertEqual(to_copper(self.char1.db.coins), 15)
        self.assertEqual(self.char1.db.bank, 15)

    def test_trainer_trains_skill_and_consumes_xp(self):
        trainer = create.create_object(TrainerNPC, key="trainer", location=self.room1)
        self.char1.db.exp = 5

        trainer.train(self.char1, "smithing")

        self.assertIsNotNone(self.char1.traits.get("smithing"))
        self.assertEqual(self.char1.traits.smithing.base, 1)
        self.assertEqual(self.char1.db.exp, 4)

    def test_guildmaster_manages_membership(self):
        guild = Guild(name="Testers", ranks=[(0, "Member")], rank_thresholds={"Member": 0})
        save_guild(guild)
        gm = create.create_object(GuildmasterNPC, key="master", location=self.room1)
        gm.db.guild = "Testers"

        gm.manage_guild(self.char1)
        _, saved = find_guild("Testers")
        self.assertEqual(self.char1.db.guild, "Testers")
        self.assertIn(str(self.char1.id), saved.members)

        gm.manage_guild(self.char1)
        _, saved = find_guild("Testers")
        self.assertEqual(saved.members[str(self.char1.id)], 1)

    def test_receptionist_greets_visitor(self):
        rec = create.create_object(GuildReceptionistNPC, key="rec", location=self.room1)
        rec.db.guild = "Adventurers Guild"
        self.char1.db.guild = ""

        rec.greet_visitor(self.char1)
        self.char1.msg.assert_called()

    def test_questgiver_offers_quest(self):
        quest = Quest(quest_key="testquest", title="A Test")
        save_quest(quest)
        giver = create.create_object(QuestGiverNPC, key="giver", location=self.room1)

        giver.offer_quest(self.char1, "testquest")
        self.assertIn("testquest", self.char1.db.active_quests)

    def test_eventnpc_starts_event(self):
        npc = create.create_object(EventNPC, key="eventer", location=self.room1)
        npc.start_event(self.char1, "party")
        self.assertEqual(npc.db.active_event, "party")
