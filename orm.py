import json  

SQL_MODEL_UNION = "UNION"
  
class JsonSerializableObject(object):
    """An object that can be serialized as JSON"""
    
    def toJson(self):
        """Returns a JSON string representation of this object."""
        return json.dumps(self, default=lambda obj: { k: obj.__dict__[k] for k in obj.__dict__ if not k.startswith("_")})
        
class ModelField(object):
    """Represents a field within a Model."""
    
    def __init__(self, *args, **kwargs):
        """Initializes a ModelField with information on how to construct its values.
        
        Arguments:
            name - The name of the field. 
            aliases (optional) - A list of column names that represent this field's value in a dictionary. )
            model (optional) - A Model class, if this field is a reference to a Model.
            required (optional) - A Boolean stating whether this field is required or not.
            key (optional) - A Boolean stating whether this field can be used to uniquely identify the model.
            type (optional) - A python type to cast the value of this field to. 
            sqltype (optional) - A string representing the type to use in a SQL column definition, or
                SQL_MODEL_UNION if this field should be flattened into the parent Model's table. 
        """
        order = ("name", "aliases", "model", "required", "key", "type", "default", "sqltype")
        num_args = len(args)
        for i in range(len(order)):
            setattr(self, order[i], args[i] if i < num_args else None)
        for key in kwargs:
            setattr(self, key, kwargs[key])
        
    def get_value(self, *args, **kwargs):
        """Gets the value of this field, given a dictionary containing one of this field's name or aliases.
        
        Arguments:
            rowdict - A dictionary representing a row containing this field's value, keyed on either this field's
                name, or one of its aliases.
        """
        rowdict = args[0] 
        if self.model is not None:
            # This is a reference to another model... create it now
            value = self.model.get(rowdict)
        else:
            try:
                value = rowdict[self._cached_alias]
            except AttributeError:
                key = self.name
                value = rowdict.get(key, None)
                i = 0
                num_aliases = len(self.aliases) if self.aliases is not None else 0
                while value is None and i < num_aliases:
                    key = self.aliases[i]
                    value = rowdict.get(key, None)
                    i += 1
                self._cached_alias = key

        if self.type is not None:
            try:
                value = self.type(value)
            except ValueError:
                value = self.default
        
        return value
    
    def get_column_definition(self):
        """Get the string defining a SQL column to store this field's value."""
        return "%s %s"%(self.name, self.sqltype)

def get_all_fields(*args):
    """Get all fields in a list of Models
    
    Arguments:
        *args - variable length list of Models to pull fields from. 
    """
    fields = []
    for cls in args:
        fields.extend([f for f in cls.__dict__.iteritems() if isinstance(f[1], ModelField)])
        for field in fields:
            if field[1].sqltype == SQL_MODEL_UNION:
                fields.remove(field)
                fields.extend(get_all_fields(field[1].model))
    return fields

class Model(JsonSerializableObject):
    """Represents a structured object pulled from a database or CSV file. """
    def __init__(self, *args, **kwargs):
        """Initializes each field in this Model with values from a dictionary. 
        
        Arguments:
            rowdict - A dictionary containing a value for each required field in this Model, keyed on 
                either the field's name or one of its aliases. 
        """
        fields = get_all_fields(self.__class__)
        for field in fields:
            setattr(self, field[0], field[1].get_value(*args, **kwargs))
    
    @classmethod
    def get_key_field(cls):
        """Gets a Model subclass's key field, which uniquely identifies each instance of that Model."""
        try:
            key_field = cls._key
        except AttributeError:
            fields = get_all_fields(cls)
            try:
                key_index = [f[1].key for f in fields].index(True)
                key_field = fields[key_index][1]
                cls._key = key_field
            except ValueError:
                return None
        return key_field
    
    @classmethod
    def get_key(cls, rowdict):
        """Gets the key field for this Model class from a dictionary containing the key, or None if no such value exists."""
        key_field = cls.get_key_field()
                
        return key_field.get_value(rowdict)
        
    @classmethod
    def get(cls, *args, **kwargs):
        """Gets an instance of a Model class. Useful for overriding in subclasses that might intern complex instances."""
        return cls(*args, **kwargs)

class ModelTableBuilder(object):
    """Given a set of models, provides methods for building and populating a SQL table with its values."""
    def __init__(self, name, models, indexes = None):
        """Initializes a ModelTableBuilder with a table name, a list of models to store in it, and a list of indexes to create.
        """
        self.name = name
        self.columns = get_all_fields(*models) if isinstance(models, list) else get_all_fields(models)
        self.indexes = {} if indexes is None else indexes
        
    def get_create_index_statements(self):
        """Gets a list of SQL statements for creating the indexes designated on this table."""
        statements = []
        for name in self.indexes:
            statements.append("CREATE INDEX IF NOT EXISTS %s on %s(%s)"%(name, self.name, ", ".join(c for c in self.indexes[name])))
    
        return statements
        
    def get_column_definitions(self):
        """Get the SQL column definitions for this table. """
        return ", ".join(c[1].get_column_definition() for c in self.columns)
        
    def get_create_statement(self):
        """Gets the SQL CREATE statement for creating this table."""
        return "CREATE TABLE IF NOT EXISTS %s(%s)" % (self.name, self.get_column_definitions())
        
    def get_insert_statement(self):
        """Gets a SQL INSERT statement for inserting values into this table, including wildcards."""
        column_names = ", ".join(c[1].name for c in self.columns)
        wildcards = ",".join("?"*len(self.columns))
        return "insert into %s(%s) values(%s)"%(self.name, column_names, wildcards)
        
    def create(self, cursor):
        """Creates the table represented by this builder."""
        print self.get_create_statement()
        cursor.execute(self.get_create_statement())
        index_statements = self.get_create_index_statements()
        for statement in index_statements:
            print statement
            cursor.execute(statement)
        
    def get_values_from_reader(self, reader):
        """Gets values from the given dictionary reader to bulk load data into this builder's table."""
        for row in reader:
            yield [col[1].get_value(row) for col in self.columns]

    def bulk_load(self, cursor, csv_filename):
        """Bulk loads data from a given csv file into the cursor provided."""
        csv_file = open(csv_filename, "r")
        csv_reader = csv.DictReader(csv_file)
        cursor.executemany(self.get_insert_statement(), self.get_values_from_reader(csv_reader))
        csv_file.close()
        
    def create_and_load(self, cursor, csv_filename):
        """Creates this table and bulk loads the given csv file's data into it."""
        self.create(cursor)
        self.bulk_load(cursor, csv_filename)
