#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from ceilometer.tests.tempest.aodh.api import base


class TelemetryAlarmingAPITest(base.BaseAlarmingTest):

    @classmethod
    def resource_setup(cls):
        super(TelemetryAlarmingAPITest, cls).resource_setup()
        cls.rule = {'metrics': ['c0d457b6-957e-41de-a384-d5eb0957de3b'],
                    'comparison_operator': 'gt',
                    'aggregation_method': 'mean',
                    'threshold': 80.0,
                    'granularity': 70}
        for i in range(2):
            cls.create_alarm(
                gnocchi_aggregation_by_metrics_threshold_rule=cls.rule)

    @decorators.idempotent_id('1c918e06-210b-41eb-bd45-14676dd77cd7')
    def test_alarm_list(self):
        # List alarms
        alarm_list = self.alarming_client.list_alarms()

        # Verify created alarm in the list
        fetched_ids = [a['alarm_id'] for a in alarm_list]
        missing_alarms = [a for a in self.alarm_ids if a not in fetched_ids]
        self.assertEqual(0, len(missing_alarms),
                         "Failed to find the following created alarm(s)"
                         " in a fetched list: %s" %
                         ', '.join(str(a) for a in missing_alarms))

    @decorators.idempotent_id('1297b095-39c1-4e74-8a1f-4ae998cedd68')
    def test_create_update_get_delete_alarm(self):
        # Create an alarm
        alarm_name = data_utils.rand_name('telemetry_alarm')
        body = self.alarming_client.create_alarm(
            name=alarm_name, type='gnocchi_aggregation_by_metrics_threshold',
            gnocchi_aggregation_by_metrics_threshold_rule=self.rule)
        self.assertEqual(alarm_name, body['name'])
        alarm_id = body['alarm_id']
        self.assertDictContainsSubset(self.rule, body[
            'gnocchi_aggregation_by_metrics_threshold_rule'])
        # Update alarm with new rule and new name
        new_rule = {'metrics': ['c0d457b6-957e-41de-a384-d5eb0957de3b'],
                    'comparison_operator': 'eq',
                    'aggregation_method': 'mean',
                    'threshold': 70.0,
                    'granularity': 60}
        alarm_name_updated = data_utils.rand_name('telemetry-alarm-update')
        body = self.alarming_client.update_alarm(
            alarm_id,
            gnocchi_aggregation_by_metrics_threshold_rule=new_rule,
            name=alarm_name_updated,
            type='gnocchi_aggregation_by_metrics_threshold')
        self.assertEqual(alarm_name_updated, body['name'])
        self.assertDictContainsSubset(
            new_rule, body['gnocchi_aggregation_by_metrics_threshold_rule'])
        # Get and verify details of an alarm after update
        body = self.alarming_client.show_alarm(alarm_id)
        self.assertEqual(alarm_name_updated, body['name'])
        self.assertDictContainsSubset(
            new_rule, body['gnocchi_aggregation_by_metrics_threshold_rule'])
        # Get history for the alarm and verify the same
        body = self.alarming_client.show_alarm_history(alarm_id)
        self.assertEqual("rule change", body[0]['type'])
        self.assertIn(alarm_name_updated, body[0]['detail'])
        self.assertEqual("creation", body[1]['type'])
        self.assertIn(alarm_name, body[1]['detail'])
        # Delete alarm and verify if deleted
        self.alarming_client.delete_alarm(alarm_id)
        self.assertRaises(lib_exc.NotFound,
                          self.alarming_client.show_alarm, alarm_id)

    @decorators.idempotent_id('aca49486-70bb-4016-87e0-f6131374f742')
    def test_set_get_alarm_state(self):
        alarm_states = ['ok', 'alarm', 'insufficient data']
        alarm = self.create_alarm(
            gnocchi_aggregation_by_metrics_threshold_rule=self.rule)
        # Set alarm state and verify
        new_state =\
            [elem for elem in alarm_states if elem != alarm['state']][0]
        state = self.alarming_client.alarm_set_state(alarm['alarm_id'],
                                                     new_state)
        self.assertEqual(new_state, state.data)
        # Get alarm state and verify
        state = self.alarming_client.show_alarm_state(alarm['alarm_id'])
        self.assertEqual(new_state, state.data)
