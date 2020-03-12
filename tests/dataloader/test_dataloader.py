import copy
import random
import operator
from collections import OrderedDict
from typing import List

import pytest
from pytest_mock import mocker
import numpy
import numpy as np

from cotk.dataloader import GeneralVocab, SimpleTokenizer, SentenceDefault, LanguageProcessing, \
	Field, Vocab, Tokenizer, FieldContext, VocabContext

class TestLanguageProcessing():
	def base_test_init(self, lp: LanguageProcessing):
		assert isinstance(lp.file_id, str)
		assert isinstance(lp.file_path, str)
		for set_name, fields in lp.fields.items():
			assert isinstance(set_name, str)
			assert isinstance(fields, dict)
			for field_name, field in fields.items():
				assert isinstance(field_name, str)
				assert isinstance(field, Field)

		assert isinstance(lp.vocabs, list)
		for vocab in lp.vocabs:
			assert isinstance(vocab, Vocab)
		assert isinstance(lp.tokenizers, list)
		for toker in lp.tokenizers:
			assert isinstance(toker, Tokenizer)

		assert lp.default_field_set_name is None
		assert lp.default_field_name is None
		for (_, data), (_, index) in zip(lp.data.items(), lp.index.items()):
			assert isinstance(data, dict)
			assert isinstance(index, list)
			for field_name, content in data.items():
				assert isinstance(content, dict)
				for _, each_content in content.items():
					assert isinstance(each_content, list)
					assert len(index) == len(each_content)
		for _, batch_id in lp.batch_id.items():
			assert batch_id == 0
		for _, batch_size in lp.batch_size.items():
			assert batch_size is None
			assert batch_size is None

	def base_test_set_default_field(self, lp: LanguageProcessing):
		for set_name, data in lp.data.items():
			with pytest.raises(KeyError):
				lp.set_default_field('unknown_set', 'unknown_field')
			for field_name, _ in data.items():
				with pytest.raises(KeyError):
					lp.set_default_field(set_name, 'unknown_field')
				lp.set_default_field(set_name, field_name)
				assert lp.default_field_set_name == set_name
				assert lp.default_field_name == field_name

	def base_test_get_default_field(self, lp: LanguageProcessing):
		for set_name, data in lp.data.items():
			for field_name, _ in data.items():
				tmp_lp = copy.deepcopy(lp)
				with pytest.raises(RuntimeError):
					tmp_lp.get_default_field()
				tmp_lp.set_default_field(set_name, field_name)
				assert tmp_lp.get_default_field() == tmp_lp.fields[set_name][field_name]

	def base_test_get_default_vocab(self, lp: LanguageProcessing):
		for set_name, data in lp.data.items():
			for field_name, _ in data.items():
				tmp_lp = copy.deepcopy(lp)
				with pytest.raises(RuntimeError):
					tmp_lp.get_default_vocab()
				tmp_lp.set_default_field(set_name, field_name)
				assert tmp_lp.get_default_vocab() == tmp_lp.fields[set_name][field_name].get_vocab()

	def base_test_get_default_tokenizer(self, lp: LanguageProcessing):
		for set_name, data in lp.data.items():
			for field_name, _ in data.items():
				tmp_lp = copy.deepcopy(lp)
				with pytest.raises(RuntimeError):
					tmp_lp.get_default_tokenizer()
				tmp_lp.set_default_field(set_name, field_name)
				assert tmp_lp.get_default_tokenizer() == tmp_lp.fields[set_name][field_name].get_tokenizer()

	def base_test_get_field(self, lp: LanguageProcessing):
		for set_name, data in lp.data.items():
			for field_name, _ in data.items():
				assert lp.get_field(set_name, field_name) == lp.fields[set_name][field_name]

	def base_test_restart(self, lp: LanguageProcessing):
		with pytest.raises(ValueError):
			lp.restart("unknown set")
		for set_name in lp.data.keys():
			with pytest.raises(ValueError):
				lp.restart(set_name)
			record_index = copy.copy(lp.index[set_name])
			lp.restart(set_name, batch_size=3, shuffle=False)
			assert record_index == lp.index[set_name]
			assert lp.batch_id[set_name] == 0
			assert lp.batch_size[set_name] == 3
			#rng_state_st = random.getstate()
			lp.restart(set_name, shuffle=True)
			#rng_state_ed = random.getstate()
			#assert operator.eq(rng_state_st, rng_state_ed)
			assert lp.batch_id[set_name] == 0
			record_index = copy.copy(lp.index[set_name])
			lp.restart(set_name, shuffle=False)
			assert record_index == lp.index[set_name]
			assert lp.batch_id[set_name] == 0

	def base_test_get_batch(self, lp: LanguageProcessing):
		with pytest.raises(ValueError):
			lp.get_batch("unknown set", [0, 1])
		for set_name in lp.data.keys():
			with pytest.raises(IndexError):
				length = len(lp.index[set_name])
				lp.get_batch(set_name, [length-1, length])
			assert len(lp.index[set_name]) >= 2
			batch = lp.get_batch(set_name, [0, 1])
			for field_name, content in batch.items():
				assert len(content) == 2

	def base_test_get_next_batch(self, lp: LanguageProcessing):
		with pytest.raises(ValueError):
			lp.get_next_batch("unknown set")
		for set_name in lp.data.keys():
			with pytest.raises(RuntimeError):
				lp.get_next_batch(set_name)

			lp.restart(set_name, 7)
			sample_num = 0
			while True:
				batch = lp.get_next_batch(set_name, ignore_left_samples=True)
				if not batch:
					break
				for field_name, content in batch.items():
					assert len(content) == 7
				sample_num += 7
			for field_name, content in lp.data[set_name].items():
				assert isinstance(content, dict)
				assert sample_num + 7 >= len(content)

	def base_test_convert(self, lp: LanguageProcessing):
		lp.set_default_field('train', 'sent')

		sent_id = [0, 1, 2]
		sent = ["<pad>", "<unk>", "<go>"]
		assert sent == lp.convert_ids_to_tokens(sent_id)
		assert sent_id == lp.convert_tokens_to_ids(sent)

		sent = ["<unk>", "<go>", "<pad>", "<unkownword>", "<pad>", "<go>"]
		sent_id = [1, 2, 0, 1, 0, 2]
		assert sent_id == lp.convert_tokens_to_ids(sent)
		assert sent_id == lp.convert_tokens_to_ids(sent, only_frequent_word=True)

		sent = [lp.all_vocab_list[lp.frequent_vocab_size]]
		assert [1] == lp.convert_tokens_to_ids(sent, only_frequent_word=True)
		assert [lp.frequent_vocab_size] == lp.convert_tokens_to_ids(sent)

		sent_id = [0, 1, 2, 0, 0, 3, 1, 0, 0]
		sent = ["<pad>", "<unk>", "<go>", "<pad>", "<pad>", "<eos>", "<unk>", "<pad>", "<pad>"]
		assert sent == lp.convert_ids_to_tokens(sent_id, trim=False)
		sent = ["<pad>", "<unk>", "<go>"]
		assert sent == lp.convert_ids_to_tokens(sent_id)

		sent_id = [0, 0, 3]
		sent = ["<pad>", "<pad>", "<eos>"]
		assert sent == lp.convert_ids_to_tokens(sent_id, remove_special=False, trim=False)
		assert not lp.convert_ids_to_tokens(sent_id)

		sent_id = [3, 3, 3]
		sent = ["<eos>", "<eos>", "<eos>"]
		assert sent == lp.convert_ids_to_tokens(sent_id, remove_special=False, trim=False)
		assert not lp.convert_ids_to_tokens(sent_id)

		sent_id = [0, 0, 0]
		sent = ["<pad>", "<pad>", "<pad>"]
		assert sent == lp.convert_ids_to_tokens(sent_id, trim=False)
		assert not lp.convert_ids_to_tokens(sent_id)

def load_LanguageProcessing1(): # Dict[str, OrderedDict[str, Field]]
	def _load_LanguageProcessing():
		file_id = './tests/dataloader/dummy_mscoco#MSCOCO'
		set_names = ['train', 'dev', 'test']
		vocab = GeneralVocab(3)
		toker = SimpleTokenizer('space', ['<pad>', '<unk>', '<go>', '<eos>'])
		sent = SentenceDefault(toker, vocab, convert_to_lower_letter=True)
		fields = {set_name: OrderedDict({'sent': sent}) for set_name in set_names}
		return LanguageProcessing(file_id, fields)
	return _load_LanguageProcessing

def load_LanguageProcessing2(): # OrderedDict[str, Field]
	def _load_LanguageProcessing():
		file_id = './tests/dataloader/dummy_mscoco#MSCOCO'
		vocab = GeneralVocab(3)
		toker = SimpleTokenizer('space', ['<pad>', '<unk>', '<go>', '<eos>'])
		sent = SentenceDefault(toker, vocab, convert_to_lower_letter=True)
		fields = OrderedDict({'sent': sent})
		return LanguageProcessing(file_id, fields)
	return _load_LanguageProcessing

def load_LanguageProcessing3(): # OrderedDict[str, str]
	def _load_LanguageProcessing():
		file_id = './tests/dataloader/dummy_mscoco#MSCOCO'
		fields = OrderedDict({'sent': 'SentenceDefault'})
		with VocabContext.set_parameters(min_frequent_vocab_times=3):
			with FieldContext.set_parameters(tokenizer='space'):
				return LanguageProcessing(file_id, fields)
	return _load_LanguageProcessing

def load_LanguageProcessing4(): # Dict[str, OrderedDict[str, str]]
	def _load_LanguageProcessing():
		file_id = './tests/dataloader/dummy_mscoco#MSCOCO'
		set_names = ['train', 'dev', 'test']
		fields = {set_name: OrderedDict({'sent': 'SentenceDefault'}) for set_name in set_names}
		with VocabContext.set_parameters(min_frequent_vocab_times=3):
			with FieldContext.set_parameters(tokenizer='space'):
				return LanguageProcessing(file_id, fields)
	return _load_LanguageProcessing

all_load_dataloaders = [load_LanguageProcessing1(), load_LanguageProcessing2(), load_LanguageProcessing3(), load_LanguageProcessing4()]

class Test1(TestLanguageProcessing):

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_init(self, load_dataloader):
		super().base_test_init(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_set_default_field(self, load_dataloader):
		super().base_test_set_default_field(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_default_field(self, load_dataloader):
		super().base_test_set_default_field(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_default_vocab(self, load_dataloader):
		super().base_test_get_default_vocab(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_default_tokenizer(self, load_dataloader):
		super().base_test_get_default_tokenizer(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_field(self, load_dataloader):
		super().base_test_get_field(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_restart(self, load_dataloader):
		super().base_test_restart(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_batch(self, load_dataloader):
		super().base_test_get_batch(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_get_next_batch(self, load_dataloader):
		super().base_test_get_next_batch(load_dataloader())

	@pytest.mark.parametrize('load_dataloader', all_load_dataloaders)
	def test_convert(self, load_dataloader):
		super().base_test_convert(load_dataloader())