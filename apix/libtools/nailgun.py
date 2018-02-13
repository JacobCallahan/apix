# -*- encoding: utf-8 -*-
"""This module provides the capability to create a new nailgun version."""
import attr
from pathlib import Path
from logzero import logger


@attr.s()
class EntityMaker():
    api_dict = attr.ib(repr=False)
    api_name = attr.ib()
    api_version = attr.ib()

    @staticmethod
    def name_to_proper_name(entity_name):
        """Convert an entity name to a class name. ent_name => Ent Name"""
        if entity_name[-1] == 's':  # we don't want pluralized names
            entity_name = entity_name[:-1]
        return " ".join(x.capitalize() for x in entity_name.split('_'))

    @staticmethod
    def name_to_class(entity_name):
        """Convert an entity name to a class name. ent_name => EntName"""
        if entity_name[-1] == 's':  # we don't want pluralized names
            entity_name = entity_name[:-1]
        return "".join(x.capitalize() for x in entity_name.split('_'))

    @staticmethod
    def normalize_param_name(param_name):
        """Strip _id(s) and pull correct from wrong[wrong][correct]"""
        if param_name[-4:] == '_ids':
            param_name = param_name[:-4]
        elif param_name[-3:] == '_id':
            param_name = param_name[:-3]
        #strip the []'s, use the last one as the new name
        if '[' in param_name and ']' in param_name:
            param_name = param_name.split('[')[-1].replace(']', '')
        return param_name

    @staticmethod
    def get_base_params(entity_dict):
        """search create and update methods for unique parameter names"""
        param_list, names = [], []
        for method in entity_dict['methods']:
            for key in ['create', 'update']:
                if key in method:
                    for value in method[key]['parameters']:
                        clean_name = value.split('~')[0].strip()
                        if clean_name == 'id':
                            continue  # we don't want to use the id field here
                        if '_ids' in clean_name and clean_name.replace('_ids', '') in names:
                            # The name_id should take the final slot
                            index = names.index(clean_name.replace('_ids', ''))
                            names[index] = clean_name
                            param_list[index] = value
                        elif '_id' in clean_name and clean_name.replace('_id', '') in names:
                            # The name_id should take the final slot
                            index = names.index(clean_name.replace('_id', ''))
                            names[index] = clean_name
                            param_list[index] = value
                        elif clean_name in names and 'required' in value:
                            # we want to keep the required parameter
                            index = names.index(clean_name)
                            names[index] = clean_name
                            param_list[index] = value
                        elif clean_name not in names and clean_name + '_id' not in names:
                            names.append(clean_name)
                            param_list.append(value)
        return sorted(param_list)

    @staticmethod
    def get_field_type(params):
        """ there are a number of cases that aren't explicitly covered here.
        In that case, we just give it a string and see what happens.
        I've currently not deternined a time to use FloatField."""
        params = params.lower()
        name = [piece.strip() for piece in params.split("~")][0]
        if name[-3:] == '_id':
            return 'OneToOneField'
        if name[-4:] == '_ids':
            return 'OneToManyField'
        if '[mail]' in params:
            return 'EmailField'
        if '_date' in params:
            return 'DateField'
        if '[ip]' in name or name in [
                'subnet[mac]', 'subnet[network]', 'subnet[to]', 'subnet[from]',
                'subnet[dns_primary]', 'subnet[dns_secondary]'
        ]:
            return 'IPAddressField'
        if '[mask]' in name:
            return 'NetMaskField'
        if '[mac]' in params:
            return 'MACAddressField'
        if 'url' in name:
            return 'URLField'
        if 'boolean' in params or 'true, false' in params:
            return 'BooleanField'
        if 'array' in params:
            return 'ListField'
        if 'datetime' in params:
            return 'DateTimeField'
        if 'hash' in params:
            return 'DictField'
        if 'number' in params or 'integer' in params:
            return 'IntegerField'
        return 'StringField'

    @staticmethod
    def arg_override(entity_name, field_entity):
        """In some parts of Sat6's API some params refer to another entity"""
        if field_entity == 'Environment':
            if entity_name not in ['ContentViewVersion', 'Location', 'Organization']:
                field_entity = 'LifecycleEnvironment'
        return field_entity

    def get_method_paths(self, entity_name):
        """Return a dictionary of methods and their paths"""
        paths = {}
        for method in self.api_dict[entity_name]['methods']:
            for key, values in method.items():
                paths[key] = values['paths']
        return paths

    def get_base_path(self, entity_name):
        """Get the base path for the entity, based on its shortest path"""
        meth_paths = self.get_method_paths(entity_name)
        paths = meth_paths.get('list', [])
        if not paths:
            for path in meth_paths.values():
                paths.extend(path)
        # return the shortest api path, with the leading '/' removed
        return sorted(paths, key=lambda x: len(x))[0].split()[1][1:] or None

    def param_to_field(self, class_name, param):
        """Converts a parameter to a nailgun field definition.
        content_view_id  ~ optional ~ string from 2 to 128 characters...
        returns
        'content_view': entity_fields.OneToOneField(ContentView, length=(2, 128))
        """
        name, required, validator = [piece.strip() for piece in param.split("~")]
        required = 'required=True' if required == 'required' else None
        if ' from ' in validator:
            # get the length arg length=(6, 12),
            split_v = validator.split(" ")
            length = 'length=({}, {})'.format(
                int(split_v[split_v.index('from') + 1]),
                int(split_v[split_v.index('from') + 3])
            )
        else:
            length = None

        str_type = "str_type='alpha'" if 'alphanumeric' in validator else None

        param_string = "'{}': ".format(self.normalize_param_name(name))
        if name[-3:] == '_id':
            arg_name = self.name_to_class(name[:-3])
        elif name[-4:] == '_ids':
            arg_name = self.name_to_class(name[:-4])
        else:
            arg_name = None

        if arg_name:
            arg_name = self.arg_override(class_name, arg_name)
            str_type, length = None, None

        param_string += "entity_fields.{}".format('{}({})'.format(
            self.get_field_type(param), ', '.join(
                filter(None, [arg_name, required, str_type, length]))
        ))
        return param_string

    def fill_method_template(self, proper_name, method_paths):
        """Load and fill out a method template for every method"""
        logger.debug('Filling template for {}\'s methods.'.format(proper_name))
        # load the template
        ent_temp_f = Path('libs/templates/nailgun/entity_method.template')
        if not ent_temp_f.exists():
            logger.error('Unable to find {}.'.format(str(ent_temp_f.absolute())))
            return
        loaded_template = None
        with ent_temp_f.open('r+') as f_load:
            loaded_template = f_load.read()

        # fill the template for each method
        method_names = list(method_paths.keys())
        http_methods = [path[0].split()[0] for path in method_paths.values()]
        compiled_template = ""
        for name, http_method in zip(method_names, http_methods):
            temp_late = loaded_template  # hahaha get it?!
            temp_late = temp_late.replace('~~method name~~', name)
            temp_late = temp_late.replace('~~http method~~', http_method.lower())
            temp_late = temp_late.replace('~~Entity Name~~', proper_name)
            compiled_template += temp_late
        return compiled_template

    def fill_entity_template(self, entity):
        """Fill out and return an entity template, based on `entity`"""
        # get all variables
        proper_name = self.name_to_proper_name(entity)
        class_name = self.name_to_class(entity)
        field_list = self.get_base_params(self.api_dict[entity])
        field_list = ',\n            '.join(
            [self.param_to_field(class_name, param) for param in field_list])
        base_path = self.get_base_path(entity)
        method_paths = {
            method: path
            for method, path in self.get_method_paths(entity).items()
            if method not in ['list', 'create', 'update', 'destroy']
        }
        methods_paths = '\n        '.join([
            '{}\n            {}'.format(method, path[0].split()[1])
            for method, path in method_paths.items()
        ])
        method_names = ',\n                '.join(
            "'{}'".format(name) for name in method_paths.keys())

        # load the template
        ent_temp_f = Path('libs/templates/nailgun/entity_class.template')
        if not ent_temp_f.exists():
            logger.error('Unable to find {}.'.format(str(ent_temp_f.absolute())))
            return
        loaded_t = None
        with ent_temp_f.open('r+') as f_load:
            loaded_t = f_load.read()

        # fill the template
        loaded_t = loaded_t.replace('~~EntityClass~~', class_name)
        loaded_t = loaded_t.replace('~~Entity Name~~', proper_name)
        loaded_t = loaded_t.replace('~~Field List~~', field_list)
        loaded_t = loaded_t.replace('~~base path~~', base_path)
        loaded_t = loaded_t.replace('~~methods paths~~', methods_paths)
        loaded_t = loaded_t.replace('~~method names~~', method_names)
        loaded_t = loaded_t.replace('~~entity methods~~',
            self.fill_method_template(proper_name, method_paths))
        return loaded_t

    def create_entities_file(self):
        """Populate an entities.py with filled entity templates"""
        logger.debug('Creating entities.py file.')
        all_entity_templates = '\n\n'.join([
            self.fill_entity_template(entity)
            for entity in self.api_dict
        ])

        entities_file = Path('libs/templates/nailgun/entities.py.template')
        if not entities_file.exists():
            logger.error('Unable to find {}.'.format(str(entities_file)))
            return
        loaded_ent_f = None
        with entities_file.open('r+') as ent_file:
            loaded_ent_f = ent_file.read()
        loaded_ent_f = loaded_ent_f.replace(
            '~~generated entity classes~~', all_entity_templates)

        save_file = Path('libs/generated/nailgun/{}/entities.py'.format(
            self.api_version))
        if save_file.exists():
            logger.warning('Overwriting {}'.format(str(save_file)))
            save_file.unlink()
        # create the directory, if it doesn't exist
        save_file.parent.mkdir(parents=True, exist_ok=True)
        save_file.touch()
        logger.info('Saving results to {}'.format(save_file))
        with save_file.open('w+') as outfile:
            outfile.write(loaded_ent_f)


@attr.s()
class NailgunMaker():
    api_dict = attr.ib(repr=False)
    api_name = attr.ib()
    api_version = attr.ib()

    def make(self):
        """Make all the changes needed to create a nailgun version"""
        entity_maker = EntityMaker(self.api_dict, self.api_name, self.api_version)
        entity_maker.create_entities_file()
