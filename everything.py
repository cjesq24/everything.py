from docassemble.base.util import *
import requests, datetime, pypdftk, copy, time, unicodedata, re
from bs4 import BeautifulSoup
from markdown import markdown
from dateutil import relativedelta
from functools import reduce
from hellosign_sdk import HSClient

# miscutil.py

def empty_string():
	return ""

def cl_array_access(array, _index):
	index = _index - 1
	return (array[index] if index < len(array) else None)

def erase(variable_name):
	undefine(variable_name)
	define("___memoized_values", {})

def floatable(arg):
	try:
		float(primitive_value(arg))
		return True
	except:
		return False

def mm_dd_yyyy_dateable(arg):
	try:
		datetime.datetime.strptime(primitive_value(arg), '%m/%d/%Y')
		return True
	except:
		return False

def iso_8601_dateable(arg):
	try:
		datetime.datetime.strptime(primitive_value(arg), '%Y-%m-%d')
		return True
	except:
		return False

def typecast_as_date(_arg):
	arg = augment(_arg)
	if is_undefined(arg) or arg.wrapped == "":
		return arg
	return augment(as_datetime(arg.wrapped))

def typecast_as_number(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	if not floatable(arg):
		return Undefined()
	return augment(float(arg.wrapped))

def typecast_as_boolean(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	wrapped = arg.wrapped
	if wrapped == 'True':
		return augment(True)
	if wrapped == 'False':
		return augment(False)
	return Undefined()

def typecast_as_string(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return augment(str(arg.wrapped))

def as_url_param_value(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return ''
	return augment(typecast_as_string(arg.wrapped))

def cl_array_map(myfunc, _myiterable):
	myiterable = augment(_myiterable)
	if is_undefined(myiterable):
		return myiterable
	return map(myfunc, myiterable.wrapped)

def cl_array_sort(myfunc, _myiterable, reverse=False):
	myiterable = augment(_myiterable)
	if is_undefined(myiterable):
		return myiterable
	return sorted(myiterable.wrapped, key=myfunc, reverse=reverse)

def cl_array_excluding_transformed_to_undefined(myfunc, _myiterable):
	# filters myiterable by excluding members for which myfunc returns undefined
	myiterable = augment(_myiterable)
	if is_undefined(myiterable):
		return myiterable
	return list(filter(lambda x: is_not_undefined(myfunc(x)), myiterable.wrapped))

def is_list(arg):
	return type(augment(arg).wrapped) == type([])

def is_dict(arg):
	return type(augment(arg).wrapped) == type({})

def as_url_param_kv_pair(key, _value, display_mapping):
	value = augment(_value)
	if is_list(value):
		if is_dict(cl_array_access(value.wrapped, 1)):
			return list_of_dicts_as_url_param_kv_pairs(key, value, display_mapping)
		else:
			pass
			# no primitive arrays yet
	elif len(str(primitive_value(value))) == 0:
		return ''
	else:
		return '&' + primitive_value(key) + "=" + primitive_value(as_url_param_value(value))

def list_of_dicts_as_url_param_kv_pairs(key, value, display_mapping):
	pairs = []
	for i, mydict in enumerate(primitive_value(value)):
		for k in primitive_value(mydict).keys():
			key_for_pair = key + '[' + str(i) + ']' + '[' + display_mapping[str(k)] + ']'
			value_for_pair = mydict[k]
			pair = '&' + str(key_for_pair) + '=' + str(value_for_pair)
			pairs.append(pair)
	return ''.join(pairs)

def list_access_with_default(list, index):
	return list[index] if index < len(list) else ''

def should_show_markdown_variable(var_name):
	return (defined(var_name) and value(var_name) != "")

def string_as_bool(something):
	return clstr(primitive_value(something)) == 'True'

def merge_two_dicts(x, y):
	z = x.copy()
	z.update(y)
	return z

def merge_list_of_dicts(my_list):
	new_dict = {}
	for existing_dict in my_list:
		new_dict.update(existing_dict)

	return new_dict

def markdown_to_plaintext(markdown_string):
	try:
		html_list = list(map(lambda str: markdown(str), markdown_string.split("\\n")))
		html_list = list(map(lambda html: re.sub(r'<pre>(.*?)</pre>', ' ', html), html_list))
		html_list = list(map(lambda html: re.sub(r'<code>(.*?)</code >', ' ', html), html_list))
		soup_list = list(map(lambda html: BeautifulSoup(html, "html.parser"), html_list))
		text_list = list(map(lambda soup: ''.join(soup.findAll(text=True)), soup_list))
		text_list = list(map(lambda text: re.sub(r'\\n', '\\n\\n', text), text_list))
		return "\\n".join(text_list)
	except:
		return markdown_string

def safe_array_access(the_array, the_index):
	try:
		return the_array[the_index]
	except:
		return None

def slice_dict(the_dict, the_keys):
	return { key:the_dict[key] for key in set(the_keys) & set(the_dict) }

def number_to_excel_column_letter(n):
	string = ""
	while n > 0:
		n, remainder = divmod(n - 1, 26)
		string = chr(65 + remainder) + string
	return string

def prepare_value_for_webhook(item):
	if isinstance(item, DADict):
		return ", ".join(item.true_values())

	return str(item)

def combine_pdfs(pdfs):
	# We filter any attachments which were conditionally excluded at runtime
	pdfs = list(filter(None, pdfs))

	if (len(pdfs) == 0):
		return None;

	output_filename = pdfs[0].info['filename'].replace('"', '').replace("'", '') + '.pdf'
	output_name = pdfs[0].info['name'].replace('"', '').replace("'", '')

	concatenated_file_path = pypdftk.concat([pdf.path() for pdf in pdfs])

	attachment_file = DAFileCollection()
	attachment_file.pdf = DAFile(filename = output_filename)
	attachment_file.pdf.copy_into(concatenated_file_path)
	attachment_file.info = {'raw': '', 'name': output_name, 'filename': output_filename, 'description': ''}

	return attachment_file

def list_selector_getter(list_target, choice_index):
	return list_target[int(choice_index)]

def list_selector_choice_generator(list_target, list_target_attribute):
	vars = cl_all_variables()
	___list_target_list = (augment(value(list_target)) if (list_target in vars) else Undefined())
	if is_not_undefined(___list_target_list):
		return [[ind, str(ind + 1) + " - " + list_item[list_target_attribute]] for (ind, list_item) in enumerate(primitive_value(___list_target_list))]

	return []

def cl_all_variables():
	define('vars', {})
	return all_variables()

def oxygenate(a_list, type_map, rawcontent_value):
	oxygenated = {}
	for idx, item in enumerate(a_list):
		oxygenated[idx] = convert_appropriate_values_to_rawcontent(item, type_map, rawcontent_value)
	return oxygenated

def convert_appropriate_values_to_rawcontent(item, type_map, rawcontent_value):
	# item is a dict (member of a loop). need to convert its richtext-type values from markdown to rawcontent
	output = {}
	for key, val in item.items():
		variable_type = type_map[key]
		if variable_type == 'richtext':
			output[key] = rawcontent_value(val)
		else:
			output[key] = val
	return output

def oxygen_legend(the_vars, type_map, wit_vars, rawcontent_value, signature_expectations={}):
	legend = { 'variables': {}, 'lists': {}, 'types': type_map }
	for var in the_vars:
		if var in type_map:
			if type_map[var] == 'richtext':
				legend['variables'][var] = { 'type': 'richtext', 'value': rawcontent_value(the_vars[var]) }
			elif type_map[var] == 'signature':
				legend['variables'][var] = { 'type': 'signature', 'value': value(var).url_for(temporary=True, seconds=60) }
			elif type_map[var] == 'array':
				legend['lists'][var] = oxygenate(the_vars[var], type_map, rawcontent_value)
			else:
				legend['variables'][var] = { 'type': type_map[var], 'value': str(the_vars[var]) }
	for wit_var in wit_vars:
		legend['variables'][wit_var] = wit_vars[wit_var]
	for signature_expectation in signature_expectations:
		legend['variables'][signature_expectation] = signature_expectations[signature_expectation]
	return legend

def serializably(something):
	try:
		return something.url_for(temporary=True, seconds=120)
	except:
		try:
			json.dumps(something)
			return something
		except:
			return str(something)

def clstr(something):
	if something is None:
		return ''
	return str(something)

def list_as_rawcontent(the_list, rawcontent, list_variable_name, separator=None):
	if is_undefined(the_list) or rawcontent == '':
		return ''
	concatenated_rawcontent = []
	for idx, item in enumerate(primitive_value(the_list)):
		working_copy = copy.deepcopy(rawcontent)
		for block in working_copy['blocks']:
			block['list_index'] = idx
			block['list_name'] = list_variable_name
			block['list_separator'] = separator
		concatenated_rawcontent.append(working_copy)
	output = copy.deepcopy(concatenated_rawcontent[0])
	output['blocks'] = []
	for individual_rawcontent_bit in concatenated_rawcontent:
		for block in individual_rawcontent_bit['blocks']:
			output['blocks'].append(block)
	return output

def add_business_days(date, number_of_days):
	days_remaining = number_of_days
	current_date = date
	saturday = 5
	sunday = 6
	while days_remaining > 0:
		current_date += relativedelta.relativedelta(days=1)
		weekday = current_date.weekday()
		if (weekday == saturday) or (weekday == sunday):
			continue
		days_remaining -= 1
	return current_date

def subtract_business_days(date, number_of_days):
	days_remaining = number_of_days
	current_date = date
	saturday = 5
	sunday = 6
	while days_remaining > 0:
		current_date -= relativedelta.relativedelta(days=1)
		weekday = current_date.weekday()
		if (weekday == saturday) or (weekday == sunday):
			continue
		days_remaining -= 1
	return current_date

def is_string(something):
	return type(primitive_value(augment(something))) == type('')

# augmented.py

class Augmented(object):
	def __init__(self, something):
		self.wrapped = something
	def __str__(self):
		return clstr(self.wrapped)
	# array
	def array_index(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(cl_array_access(self.wrapped, int(arg.wrapped)))
	def array_size(self):
		if is_undefined(self):
			return self
		return augment(len(self.wrapped))
	def array_leading(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped[:int(arg.wrapped)])
	def array_trailing(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped[int(-(arg.wrapped)):])
	def array_excluding_leading(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped[int(arg.wrapped):])
	def array_excluding_trailing(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped[:int(-(arg.wrapped))])
	# boolean
	def boolean_and(self, _arg):
		arg = augment(_arg)
		if is_false(self.wrapped) or is_false(arg.wrapped):
			return augment(False)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped and arg.wrapped)
	def boolean_or(self, _arg):
		arg = augment(_arg)
		if is_true(self.wrapped) or is_true(arg.wrapped):
			return augment(True)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped or arg.wrapped)
	def boolean_not(self):
		if is_undefined(self):
			return self
		return augment(not self.wrapped)
	def boolean_eq(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped == arg.wrapped)
	def boolean_ne(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped != arg.wrapped)
	# number
	def number_add(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped + arg.wrapped)
	def number_subtract(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped - arg.wrapped)
	def number_multiply(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped * arg.wrapped)
	def number_exponentiate(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped ** arg.wrapped)
	def number_divide(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		if arg.wrapped == 0:
			return Undefined()
		return augment(self.wrapped / arg.wrapped)
	def number_eq(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped == arg.wrapped)
	def number_ne(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped != arg.wrapped)
	def number_gt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped > arg.wrapped)
	def number_gte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped >= arg.wrapped)
	def number_lt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped < arg.wrapped)
	def number_lte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped <= arg.wrapped)
	def number_as_ordinal(self):
		if is_undefined(self):
			return Undefined()
		return augment(make_ordinal(self.wrapped))
	# string
	def string_join_with_space(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped + ' ' + arg.wrapped)
	def string_join_without_space(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped + arg.wrapped)
	def string_eq(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped == arg.wrapped)
	def string_ne(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped != arg.wrapped)
	def string_length(self):
		if is_undefined(self):
			return Undefined()
		return augment(len(self.wrapped))
	def character_at(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(list(self.wrapped)).array_index(arg)
	# time
	def time_eq(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped == arg.wrapped)
	def time_ne(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped != arg.wrapped)
	def time_gt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped > arg.wrapped)
	def time_gte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped >= arg.wrapped)
	def time_lt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped < arg.wrapped)
	def time_lte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped <= arg.wrapped)
	def time_as_hh_mm_ampm(self):
		if is_undefined(self):
			return Undefined()
		return augment(format_time(self.wrapped, format='h:mm a'))
	# date
	def date_eq(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) == arg.wrapped.replace(tzinfo=None))
	def date_ne(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) != arg.wrapped.replace(tzinfo=None))
	def date_gt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) > arg.wrapped.replace(tzinfo=None))
	def date_gte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) >= arg.wrapped.replace(tzinfo=None))
	def date_lt(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) < arg.wrapped.replace(tzinfo=None))
	def date_lte(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(self) or is_string(arg):
			return Undefined()
		return augment(self.wrapped.replace(tzinfo=None) <= arg.wrapped.replace(tzinfo=None))
	# dictionary
	def dictionary_all_false(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.all_false())
	def dictionary_all_true(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.all_true())
	def dictionary_any_false(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.any_false())
	def dictionary_any_true(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.any_true())
	def dictionary_access(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.wrapped.get(arg.wrapped))
	# case
	def to_uppercase(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.upper())
	def to_lowercase(self):
		if is_undefined(self):
			return self
		return augment(self.wrapped.lower())

	def make_clio_contacts_dictionary_access(self, clio_refresh_token):
		def clio_contacts_dictionary_access(contact_id):
			if is_undefined(self) or is_undefined(contact_id):
				return Undefined()
			___member_response = requests.get("https://app.clio.com/api/v4/contacts/" + str(primitive_value(contact_id)) + "?" + primitive_value(self).get('url_parameters'), headers=get_clio_access_headers_using_refresh_token(clio_refresh_token)).json().get('data')

			if not ___member_response:
				raise(Exception("The contact id you chose (" + str(primitive_value(contact_id)) + ") for Clio Contacts table '" + primitive_value(self).get('variable_name') + "' didn't match any of your contacts."))

			___all_field_values = {}
			___fields = primitive_value(self).get('fields')
			for field in ___fields:
				___all_field_values.update({ field.get('name'): clio_response_getter(___member_response, field.get('attribute_name'), field.get('sub_attribute_name'), field.get('selector'), field.get('mapped_to_custom_field'), field.get('picklist_mapping')) })
			return augment(___all_field_values)
		return clio_contacts_dictionary_access

	def make_clio_matters_dictionary_access(self, clio_refresh_token):
		def clio_matters_dictionary_access(matter_id):
			if is_undefined(self) or is_undefined(matter_id):
				return Undefined()
			___member_response = requests.get("https://app.clio.com/api/v4/matters/" + str(primitive_value(matter_id)) + "?" + primitive_value(self).get('url_parameters'), headers=get_clio_access_headers_using_refresh_token(clio_refresh_token)).json().get('data')

			if not ___member_response:
				raise(Exception("The matter id you chose (" + str(primitive_value(matter_id)) + ") for Clio Matters table '" + primitive_value(self).get('variable_name') + "' didn't match any of your matters."))

			___all_field_values = {}
			___fields = primitive_value(self).get('fields')
			for field in ___fields:
				___all_field_values.update({ field.get('name'): clstr(clio_response_getter(___member_response, field.get('attribute_name'), field.get('sub_attribute_name'), field.get('selector'), field.get('mapped_to_custom_field'), field.get('picklist_mapping'))) })
			return augment(___all_field_values)
		return clio_matters_dictionary_access

	def make_google_tables_dictionary_access(self, google_refresh_token):
		def google_tables_dictionary_access(key_column_value):
			if is_undefined(self) or is_undefined(key_column_value):
				return Undefined()
			___sheets_response = requests.get(primitive_value(self).get('sheets_url'), headers=get_google_access_headers(google_refresh_token)).json().get('values')
			___key_column_index = ___sheets_response[0].index(primitive_value(self).get('key_column_name'))
			___selected_row_unflattened = list(filter(lambda row: row[___key_column_index] == str(primitive_value(key_column_value)), ___sheets_response[1:]))

			if len(___selected_row_unflattened) == 0:
				raise(Exception("The index you chose (" + str(primitive_value(key_column_value)) + ") for Google table '" + primitive_value(self).get('variable_name') + "' didn't match any values found in the table."))

			___selected_row = ___selected_row_unflattened[0]
			___all_column_values = {}
			___columns = primitive_value(self).get('columns')

			for column in ___columns:
				___all_column_values.update({ column.get('name'): list_access_with_default(___selected_row, column.get('column_index')) })

			return augment(___all_column_values)
		return google_tables_dictionary_access

	def make_google_table_includes_row_with_key(self, google_refresh_token):
		def google_table_includes_row_with_key(key_column_value):
			if is_undefined(self) or is_undefined(key_column_value):
				return Undefined()
			___sheets_response = requests.get(primitive_value(self).get('sheets_url'), headers=get_google_access_headers(google_refresh_token)).json().get('values')
			___key_column_index = ___sheets_response[0].index(primitive_value(self).get('key_column_name'))
			___selected_row = list(filter(lambda row: row[___key_column_index] == str(primitive_value(key_column_value)), ___sheets_response[1:]))

			if len(___selected_row) == 0:
				return False

			return True
		return google_table_includes_row_with_key

	def google_row_index(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(self.dictionary_access(arg))

	# date math
	def days_after(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(days=+(self.wrapped)))
	def business_days_after(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(add_business_days(arg.wrapped, self.wrapped))
	def business_days_before(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(subtract_business_days(arg.wrapped, self.wrapped))
	def months_after(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(months=+(self.wrapped)))
	def years_after(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(years=+(self.wrapped)))
	def days_before(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(days=-(self.wrapped)))
	def months_before(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(months=-(self.wrapped)))
	def years_before(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg):
			return Undefined()
		return augment(arg.wrapped + relativedelta.relativedelta(years=-(self.wrapped)))
	# date formatting
	def date_format_ddmmyyyy(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='dd/MM/yyyy'))
	def date_format_mmddyyyy(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='MM/dd/yyyy'))
	def date_format_yyyymmdd(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='yyyy/MM/dd'))
	def date_format_yyyymmddhmstz(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_datetime(self.wrapped, format='yyyy-MM-dd hh:mm:ss z'))
	def date_format_mdy_month_name(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='long'))
	def date_format_mdy_month_name_day_name(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='full'))
	def date_format_yyyy(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='yyyy'))
	def date_format_month_name(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='MMMM'))
	def date_format_dd(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='dd'))
	def date_format_mm(self):
		if is_undefined(self) or is_string(self):
			return self
		return augment(format_date(self.wrapped, format='MM'))
	def date_format_day_as_ordinal_and_month(self):
		if is_undefined(self) or is_string(self):
			return self

		day_of_month = format_date(self.wrapped, format='d')
		month_name = format_date(self.wrapped, format='MMMM')
		day_as_ordinal = make_ordinal(day_of_month)

		return "%s day of %s" % (day_as_ordinal, month_name)
	def date_format_day_as_ordinal(self):
		if is_undefined(self) or is_string(self):
			return self

		day_of_month = format_date(self.wrapped, format='d')
		day_as_ordinal = make_ordinal(day_of_month)

		return str(day_as_ordinal)
	def days_since(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg) or is_string(self):
			return Undefined()
		return augment((self.wrapped - arg.wrapped).days)
	def months_since(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg) or is_string(self):
			return Undefined()
		diff = relativedelta.relativedelta(self.wrapped, arg.wrapped)
		months_diff = diff.months
		years_diff = diff.years
		return augment(months_diff + (years_diff * 12))
	def years_since(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg) or is_string(arg) or is_string(self):
			return Undefined()
		diff = relativedelta.relativedelta(self.wrapped, arg.wrapped)
		return augment(diff.years)
	# checkbox formatting
	def boolean_valued_dictionary_as_comma_delimited_list_of_true_values(self):
		if is_undefined(self):
			return Undefined()
		inner_dict = self.wrapped
		keys_for_true_values = [k for k, v in inner_dict.items() if v]
		return augment(", ".join(keys_for_true_values))
	# string typecasting
	def string_as_number(self):
		if is_undefined(self) or (not floatable(self.wrapped)):
			return Undefined()
		return augment(float(self.wrapped))
	def string_as_date_mm_dd_yyyy(self):
		if is_undefined(self) or (not mm_dd_yyyy_dateable(self.wrapped)):
			return Undefined()
		return augment(datetime.datetime.strptime(primitive_value(self.wrapped), '%m/%d/%Y'))
	def string_as_date_iso_8601(self):
		if is_undefined(self) or (not iso_8601_dateable(self.wrapped)):
			return Undefined()
		return augment(datetime.datetime.strptime(primitive_value(self.wrapped), '%Y-%m-%d'))
	def string_to_all_caps(self):
		if is_undefined(self):
			return Undefined()
		return augment(self.wrapped.upper())
	def number_format_decimal_precision(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment('{:.{prec}f}'.format(self.wrapped, prec=int(arg.wrapped)))
	def number_as_text_with_commas_separating_thousands(self):
		if is_undefined(self):
			return Undefined()
		return augment(f"{(self.wrapped):,}")
	def is_defined(self):
		return (not is_undefined(self))
	def is_not_defined(self):
		return is_undefined(self)
	def string_case_sensitively_includes(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(arg.wrapped in self.wrapped)
	def string_case_insensitively_includes(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		return augment(arg.wrapped.lower() in self.wrapped.lower())
	def cldb_table_index(self, _arg):
		arg = augment(_arg)
		if is_undefined(self) or is_undefined(arg):
			return Undefined()
		from urllib.parse import urlencode
		table_import_dict = self.wrapped
		key_value = arg.wrapped
		cldb_table_id = table_import_dict['cldb_table_id']
		access_code = table_import_dict['access_code']
		endpoint = table_import_dict['read_endpoint_base']
		full_request_url = endpoint + '?' + urlencode({ 'table_id': cldb_table_id, 'access_code': access_code, 'key_value': key_value })
		attempts = 0
		while attempts < 250:
			index_response = requests.get(full_request_url)
			as_json = index_response.json()
			success = as_json.get('success')
			if success:
				return as_json.get('object')
			elif as_json.get('message') == 'locked':
				attempts += 1
				time.sleep(.2)
			else:
				return { 'success': False }

# utility functions:

def primitive_value(something):
	return augment(something).wrapped

def Undefined():
	return augment(None)

def is_true(arg):
	return primitive_value(arg) == True

def is_false(arg):
	return primitive_value(arg) == False

def is_falsy(arg):
	wrapped = primitive_value(arg)
	return wrapped == False or wrapped == None

def is_truthy(arg):
	wrapped = primitive_value(arg)
	return not is_falsy(wrapped)

def is_augmented(something):
	return something.__class__.__name__ == 'Augmented'

def augment(something=None):
	if is_augmented(something):
		return something
	return Augmented(something)

def is_undefined(something):
	return augment(something).wrapped == None

def is_not_undefined(something):
	return not is_undefined(something)

def ternary(condition, true_value, false_value):
	if is_undefined(condition):
		return Undefined()
	elif is_true(augment(condition)):
		return primitive_value(true_value)
	else:
		return primitive_value(false_value)

# clio.py

def clio_response_getter(response_object, attribute_name, sub_attribute_name, selector, custom_field, picklist_mapping={}):
	if not response_object:
		raise(Exception("The selection you made didn't match anything found in Clio."))
	if custom_field:
		___attribute_object = list(filter(lambda item: (item.get('field_name') == attribute_name), response_object.get('custom_field_values')))
		if (len(___attribute_object) == 0):
			return '';
		value = ___attribute_object[0].get('value')
		return (picklist_mapping or {}).get(str(value)) or value
	elif (selector != ''):
		___attribute_object = list(filter(lambda item: (item.get('name') == selector), response_object.get(attribute_name)))
		if (len(___attribute_object) == 0):
			return '';
		return ___attribute_object[0].get(sub_attribute_name)
	elif (sub_attribute_name != ''):
		___attribute_object = response_object.get(attribute_name)
		if (___attribute_object == None):
			return ''
		return ___attribute_object.get(sub_attribute_name)
	else:
		return response_object.get(attribute_name) or ''

def as_ccf_update_params(custom_field_values, existing_custom_fields):
	return [as_ccf_update_param(x, existing_custom_fields) for x in custom_field_values]

def as_ccf_update_param(custom_field_value, existing_custom_fields):
	custom_field_id = custom_field_value.get('custom_field').get('id')
	existing_custom_field_ids = [field.get('custom_field').get('id') for field in existing_custom_fields]
	if custom_field_id in existing_custom_field_ids:
		existing_custom_field = next(x for x in existing_custom_fields if x.get('custom_field').get('id') == custom_field_id)
		existing_custom_field['value'] = custom_field_value.get('value')
		return existing_custom_field
	return custom_field_value

def as_cgf_update_params(precursory_grouped_update_params, existing_grouped_fields):
	___transformed_params = {}
	for group_key in precursory_grouped_update_params:
		if group_key not in ___transformed_params:
			 ___transformed_params[group_key] = []
		___objects = precursory_grouped_update_params[group_key]
		if type(___objects) == type({}):
			___transformed_params[group_key] = ___objects
		else:
			for obj in ___objects:
				___name = obj.get('name')
				___match = safe_array_access(list(filter(lambda x: x.get('name') == ___name, existing_grouped_fields[group_key])), 0)
				if ___name and ___match:
					___new_obj = copy.deepcopy(obj)
					___new_obj['id'] = ___match.get('id')
					___transformed_params[group_key] = ___transformed_params[group_key] + [___new_obj]
				else:
					___transformed_params[group_key] = ___transformed_params[group_key] + [obj]
	return ___transformed_params

def get_clio_access_token_using_refresh_token(refresh_token):
	___refresh_url = "https://app.clio.com/oauth/token"
	___refresh_data = {'client_id': get_config('clio client id'), 'client_secret': get_config('clio secret key'), 'grant_type': 'refresh_token', 'refresh_token': refresh_token}
	___refresh_response = requests.post(url = ___refresh_url, data = ___refresh_data)
	return json.loads(___refresh_response.content.decode()).get('access_token')

def get_clio_access_headers_using_refresh_token(refresh_token):
	___clio_access_token = get_clio_access_token_using_refresh_token(refresh_token)
	return {'Content-Type': 'application/json', 'Authorization': "Bearer %s" % ___clio_access_token}

# google.py

def get_google_access_headers(refresh_token):
	___discovery_document = requests.get("https://accounts.google.com/.well-known/openid-configuration")
	___refresh_url = ___discovery_document.json().get('token_endpoint')
	___refresh_data = {'client_id': get_config('google client id'), 'client_secret': get_config('google secret key'), 'grant_type': 'refresh_token', 'refresh_token': refresh_token}
	___refresh_response = requests.post(url = ___refresh_url, data = ___refresh_data)
	___google_access_token = ___refresh_response.json().get('access_token')
	return {'Content-Type': 'application/json', 'Authorization': "Bearer %s" % (___google_access_token)}

# reducers.py

def number_add_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return reduce(lambda x, y: augment(x).number_add(augment(y)), arg.wrapped)

def number_multiply_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return reduce(lambda x, y: augment(x).number_multiply(augment(y)), arg.wrapped)

def number_mean_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	size = arg.array_size()
	total = number_add_array_reducer(arg)
	return total.number_divide(size)

def number_maximum_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return max(map(primitive_value, arg.wrapped))

def number_minimum_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return min(map(primitive_value, arg.wrapped))

def boolean_all_true_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return reduce(lambda x, y: augment(x).boolean_and(augment(y)), arg.wrapped)

def boolean_any_true_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return reduce(lambda x, y: augment(x).boolean_or(augment(y)), arg.wrapped)

def boolean_all_false_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return augment(boolean_any_true_array_reducer(arg)).boolean_not()

def boolean_any_false_array_reducer(_arg):
	arg = augment(_arg)
	if is_undefined(arg):
		return arg
	return augment(boolean_all_true_array_reducer(arg)).boolean_not()

def join_with_newline(list_of_strings):
	return "\n\n".join(list_of_strings)

def join_with_oxford_comma(list_of_strings):
	if len(list_of_strings) == 0:
		return ''
	if len(list_of_strings) == 1:
		return list_of_strings[0]
	if len(list_of_strings) == 2:
		return list_of_strings[0] + ' and ' + list_of_strings[1]
	return ', '.join(list_of_strings[:-1]) + ', and ' + list_of_strings[-1]

def poorly_log(something):
	requests.get("https://community.lawyer/log?value=" + str(something))
	return ""

def benchmark(message):
	timestamp = str(datetime.datetime.now())
	requests.get("https://community.lawyer/log?message=" + str(message) + "&time=" + timestamp)
	return ""

def strip_accents(text):
	text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
	return str(text)

def as_valid_filename(the_string):
	# only retain alphanumerics + whitespace
	return re.sub(r'([^\s\w]|_)+', '', space_to_underscore(strip_accents(the_string)))

def first_file(file_or_file_list):
	try:
		return file_or_file_list[0]
	except:
		return file_or_file_list

def strip_quotes(the_string):
	return clstr(the_string or '').replace('"', '').replace("'", '')

def fine_timestamp():
	# timestamp as milliseconds
	return int(time.time() * 1000)

def clio_webhook_alert_on_failure(response, type, webhook_id, user_email, app_id, error, extra_emails=[]):
	if not response or ((not isinstance(response, dict)) and response.json().get('error') is not None):
		send_email(to=(['mikeappell@community.lawyer', 'michael@community.lawyer', 'scott@community.lawyer'] + extra_emails), subject='There was a failed Clio webhook detected', body="""
			A Clio webhook failed for %s, webhook id %s. It was sent by %s from app id %s. The error was as follows:

			%s
		"""%(type, webhook_id, user_email, app_id, error))

def remove_undefined_emails_for_clio(email_addresses_array):
	validated_email_addresses = []

	for address_dict in email_addresses_array:
		if address_dict['address'] != '' and address_dict['address'] is not None:
			validated_email_addresses.append(address_dict)

	return validated_email_addresses

def make_ordinal(n):
	'''
		see: https://stackoverflow.com/a/50992575/3439498

		Convert an integer into its ordinal representation::

		make_ordinal(0)   => '0th'
		make_ordinal(3)   => '3rd'
		make_ordinal(122) => '122nd'
		make_ordinal(213) => '213th'
	'''
	n = int(n)
	suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
	if 11 <= (n % 100) <= 13:
		suffix = 'th'
	return str(n) + suffix

def get_hellosign_client():
	return HSClient(api_key=get_config('hellosign key'))

def valid_email(email):
	return not not re.match('[^@]+@[^@]+\.[^@]+', email)
