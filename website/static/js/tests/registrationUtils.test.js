/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var faker = require('faker');

var bootbox = require('bootbox');
var utils = require('tests/utils');
var $osf = require('js/osfHelpers');

var registrationUtils = require('js/registrationUtils');
var Comment = registrationUtils.Comment; // jshint ignore:line
var Question = registrationUtils.Question;
var MetaSchema = registrationUtils.MetaSchema;
var Draft = registrationUtils.Draft;
var RegistrationEditor = registrationUtils.RegistrationEditor;
var RegistrationManager = registrationUtils.RegistrationManager;

function makeComment(data){
    data = $.extend({}, {
        value: 'foo'
    }, data || {});
    return [new Comment(data), data];
}

function makeQuestion(props, data) {
    props = $.extend({}, {
        qid: faker.internet.ip(),
        title: faker.internet.domainWord(),
        nav: faker.internet.domainWord(),
        type: 'string',
        format: 'text',
        description: faker.lorem.sentence(),
        help: faker.lorem.sentence(),
        required: true,
        options: [faker.internet.domainWord(), faker.internet.domainWord(), faker.internet.domainWord()]
    }, props || {});
    data = data || {
        value: 'Foobar'
    };
    return [new Question(props, data), props, data];
}
function makeMetaSchema() {
    var questions = [];
    for (var i = 0; i < 3; i++) {
        questions.push({
            qid: 'q' + i,
            type: 'string',
            format: 'text',
            required: true
        });
    }
    var params = {
        schema_name: 'My Schema',
        schema_version: 1,
        title: 'A schema',
        schema: {
            title: 'A schema',
            version: 1,
            description: 'A very interesting schema',
            fulfills: [],
            pages: [1, 1, 1].map(function() {
                return {
                    id: faker.internet.ip(),
                    title: 'Page',
                    questions: questions
                };
            })
        },
        id: 'asdfg'
    };

    var data = {};
    $.each(questions, function(_, question) {
        data[question.qid] = {
            value: null,
            comments: []
        };
    });
    var ms = new MetaSchema(params, data);
    return [ms, params];
}

describe('Comment', () => {
    sinon.collection.restore();
    beforeEach(() => {
        window.contextVars.currentUser = {
            fullname: faker.name.findName(),
            id: 1
        };        
    });
    
    describe('#constructor', () => {
        it('loads in optional instantiation data', () => {
            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence(),
                isDeleted: true
            };
            var comment = new Comment(data);
            assert.equal(comment.user, user);
            assert.equal(comment.lastModified.toString(), new Date(data.lastModified).toString());
            assert.equal(comment.value(), data.value);
            assert.equal(comment.isDeleted(), true);
        });
        it('defaults user to the global currentUser', () => {
            var comment = new Comment();
            assert.deepEqual(comment.user, $osf.currentUser());
        });
    });
    describe('#saved', () => {
        it('is true if the comment has data', () => {
            var comment = new Comment();
            assert.isFalse(comment.saved());

            comment = new Comment({
                user: {
                    fullname: faker.name.findName(),
                    id: 2
                },
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            });
            assert.isTrue(comment.saved());
        });
    });
    describe('#isDeleted', () => {
        it('is true when a comment is deleted and sets the value to a deleted message', () => {
            var comment = new Comment();
            assert.isFalse(comment.isDeleted());
            comment.isDeleted(true);
            assert.isTrue(comment.isDeleted());
            assert.equal(comment.value(), '');

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.isDeleted());
            comment.isDeleted(true);
            assert.isTrue(comment.isDeleted());
            assert.equal(comment.value(), '');
        });
    });
    describe('#seenBy', () => {
        it('defaults to a list containing the current user\'s id', () => {
            var comment = new Comment();
            var currentUser = window.contextVars.currentUser;
            assert.isTrue(comment.seenBy().length === 1);
            assert.deepEqual(comment.seenBy(), [currentUser.id]);
        });
    });
    describe('#isOwner', () => {
        it('returns true if the current user is the comment creator, else false', () => {
            var comment = new Comment();
            var currentUser = window.contextVars.currentUser;
            assert.isTrue(comment.isOwner());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.isOwner());
        });
    });
    describe('#author', () => {
        it('is always the user who creates the comment\'s fullname', () => {
            var comment = new Comment();
            assert.isTrue(comment.author() === window.contextVars.currentUser.fullname);

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isTrue(comment.author() === user.fullname);
        });
    });
    describe('#getAuthor', () => {
        it('returns \'You\' if the current user is the commenter else the commenter name', () => {
            var comment = new Comment();
            assert.isTrue(comment.getAuthor() === 'You');

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isTrue(comment.getAuthor() === user.fullname);
        });
    });
    describe('#canDelete', () => {
        it('is true if the global currentUser is the same as comment.user', () => {
            var comment = new Comment();
            assert.isTrue(comment.canDelete());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.canDelete());
        });
    });
    describe('#canEdit', () => {
        it('is true if the comment is saved and the current user is the comment creator', () => {
            var comment = new Comment();
            assert.isFalse(comment.canEdit());
            comment.saved(true);
            assert.isTrue(comment.canEdit());

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment = new Comment(data);
            assert.isFalse(comment.canEdit());
            comment.saved(true);
            assert.isFalse(comment.canEdit());
        });
    });
    describe('#viewComment', () => {
        it('adds a user id that is not the author to a the seenBy array', () => {
            var comment = new Comment();
            var currentUser = window.contextVars.currentUser;

            var user = {
                fullname: faker.name.findName(),
                id: 2
            };
            var data = {
                user: user,
                lastModified: faker.date.past(),
                value: faker.lorem.sentence()
            };
            comment.viewComment(user);
            assert.isTrue(comment.seenBy().length === 2);
            assert.isTrue(comment.seenBy().indexOf(user.id) !== -1);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);

            comment = new Comment(data);
            comment.viewComment(currentUser);
            assert.isTrue(comment.seenBy().length === 2);
            assert.isTrue(comment.seenBy().indexOf(user.id) !== -1);
            assert.isTrue(comment.seenBy().indexOf(currentUser.id) !== -1);
        });
    });
});

describe('Question', () => {
    sinon.collection.restore();
    var q;
    var question;
    var data;
    before(() => {
        var parts = makeQuestion();
        q = parts[0];
        question = parts[1];
        data = parts[2];
    });
    describe('#constructor', () => {
        it('loads in optional instantiation data', () => {
            assert.equal(q.id, question.qid);
            assert.equal(q.title, question.title);
            assert.equal(q.nav, question.nav);
            assert.equal(q.type, question.type);
            assert.equal(q.format, question.format);
            assert.equal(q.description, question.description);
            assert.equal(q.help, question.help);
            assert.equal(q.required, question.required);
            assert.equal(q.options, question.options);
            assert.equal(q.value(), data.value);
        });
        it('maps object-type Question\'s properties property to sub-Questions', () => {
            var props = {
                foo: {
                    type: 'number'
                }
            };
            var obj = new Question({
                qid: 'foo',
                type: 'object',
                properties: props
            }, {});
            assert.equal(obj.properties.foo.id, 'foo');
            assert.isDefined(obj.properties.foo.value);
        });
        it('maps comments into Comment instances', () => {
            var question = makeQuestion(null, {
                comments: [makeComment()[1], makeComment()[1]]
            })[0];
            var comments = question.comments();
            assert.equal(comments.length, 2);
            assert.equal(comments[0].user.id, $osf.currentUser().id);
            assert.equal($.type(comments[0].created), 'date');
        });
        it('is required if is not object type and required', () => {
            var question = makeQuestion({
                required: false
            })[0];
            assert.isFalse(question.required);
            question = makeQuestion({
                required: true
            })[0];
            assert.isTrue(question.required);
        });
        it('is required if object type and and property is required', () => {
            var p1 = makeQuestion({required: true})[1];
            var p2 = makeQuestion({required: false})[1];

            var question = makeQuestion({
                required: false,
                type: 'object',
                properties: {
                    p1: p1,
                    p2: p2
                }
            })[0];
            assert.isTrue(question.required);
        });
    });
    describe('#allowAddNext', () => {
        it('is true if the Question\'s nextComment is not blank', () => {
            assert.isFalse(q.allowAddNext());
            q.nextComment('not blank');
            assert.isTrue(q.allowAddNext());
        });
    });
    describe('#isComplete', () => {
        it('is true if the Question\'s value is not blank', () => {
            q.value(null);
            assert.isFalse(q.isComplete());
            q.value('not blank');
            assert.isTrue(q.isComplete());
        });
    });
    describe('#isValid', () => {
        it('is true if the Question\'s value is not empty and the question is required', () => {
            q.value(null);
            assert.isFalse(q.value.isValid());
            q.value('not empty');
            assert.isTrue(q.value.isValid());
        });
    });
    describe('#addComment', () => {
        it('creates a new Comment using the value of Question.nextComment, and clears Question.nextComment', () => {
            assert.equal(q.comments().length, 0);
            q.nextComment('A good comment');
            q.addComment(function() {});
            assert.equal(q.comments().length, 1);
            assert.equal(q.nextComment(), '');
        });
        it('calls the provided save function'), () => {
            var mock = new sinon.spy();
            q.nextComment('A comment');
            q.addComment(mock);
            assert.isTrue(mock.called);
        };
    });
    describe('#toggleExample', () => {
        it('toggles the value of Question.showExample', () => {
            assert.isFalse(q.showExample());
            q.toggleExample();
            assert.isTrue(q.showExample());
        });
    });
});

describe('MetaSchema', () => {
    sinon.collection.restore();
    describe('#constructor', () => {
        it('loads optional instantion data and maps question data to Question instances', () => {

            var ctx = makeMetaSchema();
            var ms = ctx[0];
            var params = ctx[1];
            assert.equal(ms.name, params.schema_name);
            assert.equal(ms.version, params.schema_version);
            assert.equal(ms.schema.pages[0].id, params.schema.pages[0].id);

            assert.isDefined(ms.pages[2].questions[0].value);
        });
    });
    describe('#flatQuestions', () => {
        it('creates a flat array of the schema questions', () => {
            var ctx = makeMetaSchema();
            var ms = ctx[0];
            var params = ctx[1];

            var questions = [];
            $.each(params.schema.pages, function(i, page) {
                $.each(page.questions, function(qid, question) {
                    questions.push(question);
                });
            });
            var flatQuestions = ms.flatQuestions();
            $.each(questions, function(i, question) {
                assert.equal(flatQuestions[i].id, question.qid);
                assert.equal(flatQuestions[i].type, question.type);
                assert.equal(flatQuestions[i].format, question.format);
            });
        });
    });
});

describe('Draft', () => {
    sinon.collection.restore();
    var ms = makeMetaSchema()[0];

    var beforeRegisterUrl = faker.internet.ip();
    var registerUrl = faker.internet.ip();
    var params = {
        pk: faker.random.number(),
        registration_metadata: {},
        initiator: {
            name: faker.name.findName(),
            id: faker.internet.ip()
        },
        initiated: faker.date.past(),
        updated: faker.date.past(),
        urls: {
            before_register: beforeRegisterUrl,
            register: registerUrl
        }
    };

    var draft = new Draft(
        params, ms
    );

    describe('#constructor', () => {
        it('loads optional instantiation data and metaSchema instance', () => {
            assert.equal(draft.metaSchema.name, ms.name);
            assert.equal(draft.initiator.id, params.initiator.id);
            assert.equal(draft.updated.toString(), params.updated.toString());
        });
        /* TODO(samchrisinger): update me
        it('calculates a percent completion based on the passed registration_metadata', () => {
            var ms = makeMetaSchema()[2];

            var data = {};
            var questions = ms.flatQuestions();
            $.each(questions, function(i, q) {
                q.value('value');
                data[q.id] = {
                    value: 'value'
                };
            });

            var params = {
                pk: faker.random.number(),
                registration_metadata: data,
                initiator: {
                    name: faker.name.findName(),
                    id: faker.internet.ip()
                },
                initiated: faker.date.past(),
                updated: faker.date.past()
            };

            var draft = new Draft(params, ms);
            assert.equal(draft.completion(), 100);
        });
         */
    });
    describe('#beforeRegister', () => {
        var endpoints = [{
            method: 'GET',
            url: beforeRegisterUrl,
            response: {
                errors: ['Error'],
                prompts: ['Prompt']
            }
        }];
        var server;
        var getJSONSpy;
        var preRegisterErrorsStub;
        var preRegisterPromptsStub;
        var registerStub;
        before(() => {
            server = utils.createServer(sinon, endpoints);
            getJSONSpy = sinon.spy($, 'getJSON');
            preRegisterErrorsStub = sinon.stub(draft, 'preRegisterErrors');
            preRegisterPromptsStub = sinon.stub(draft, 'preRegisterPrompts');
            registerStub = sinon.stub(draft, 'register');
        });
        after(() => {
            server.restore();
            $.getJSON.restore();
            draft.preRegisterErrors.restore();
            draft.preRegisterPrompts.restore();
            draft.register.restore();
        });
        afterEach(() => {
            preRegisterErrorsStub.reset();
            preRegisterPromptsStub.reset();
            registerStub.reset();
        });
        it('fetches pre-register messages', (done) => {
            draft.beforeRegister().always(function() {
                assert.isTrue(getJSONSpy.calledOnce);
                done();
            });
        });
        it('calls Draft#preRegisterErrors if there are errors', (done) => {
            draft.beforeRegister().always(function() {
                assert.isTrue(preRegisterErrorsStub.calledOnce);
                done();
            });
        });
        it('calls Draft#preRegisterPrompts if there are prompts and no errors', (done) => {
            server.respondWith(
                beforeRegisterUrl,
                function (xhr, id) {
                    xhr.respond(200,
                                {'Content-Type': 'application/json'},
                                JSON.stringify({
                                    prompts: ['Warn']
                                }));
                });
            draft.beforeRegister().always(function() {
                assert.isTrue(preRegisterPromptsStub.calledOnce);
                done();
            });
        });
        it('calls Draft#register if there are no errors and no prompts', (done) => {
            server.respondWith(
                beforeRegisterUrl,
                '{}'
            );
            draft.beforeRegister().always(function() {
                assert.isTrue(preRegisterPromptsStub.called);
                done();
            });
        });
    });
    describe('#register', () => {
        var server;
        var postJSONStub;
        var dialogStub;
        before(() => {
            server = utils.createServer(sinon, []);
            postJSONStub = sinon.stub($osf, 'postJSON', function() {
                return $.Deferred();
            });
            dialogStub = sinon.stub(bootbox, 'dialog');
        });
        after(() => {
            server.restore();
            $osf.postJSON.restore();
            bootbox.dialog.restore();
        });
        it('POSTS the data passed into beforeRegister, and redirects on a success response', (done) => {
            server.respondWith(
                beforeRegisterUrl,
                '{}'
            );
            var data = {some: 'data'};
            draft.beforeRegister(data).always(() => {
                assert.isTrue(dialogStub.called);
                done();
            });
        });
    });
});

describe('RegistrationEditor', () => {
    sinon.collection.restore();
    var ms = makeMetaSchema()[0];
    var questions = ms.flatQuestions();

    var metaData = {};
    $.each(questions, function(i, q) {
        var value = faker.company.bsNoun();
        metaData[q.id] = value;
        //q.value(value);
    });

    var beforeRegisterUrl = faker.internet.ip();
    var registerUrl = faker.internet.ip();
    var params = {
        pk: faker.random.number(),
        registration_metadata: metaData,
        initiator: {
            name: faker.name.findName(),
            id: faker.internet.ip()
        },
        initiated: faker.date.past(),
        updated: faker.date.past(),
        urls: {
            before_register: beforeRegisterUrl,
            register: registerUrl
        }
    };

    var draft = new Draft(
        params, ms
    );

    var editor;
    var createUrl = faker.internet.ip();
    var updateUrl = faker.internet.ip() + '/{draft_pk}/';
    before(() => {
        editor = new RegistrationEditor({
            create: createUrl,
            update: updateUrl
        }, '#id');
        editor.init(draft);
    });
    describe('#init', () => {
        it('loads draft data', () => {
            assert.equal(editor.draft(), draft);
        });
        /* TODO(samchrisinger): update tests
        it('#loads schema data into the schema', () => {
            $.each(questions, function(i, q) {
                assert.equal(q.value(), metaData[q.id].value);
            });
        });
         */
    });
    describe('#create', () => {
        var postJSONStub;
        var updateDataStub;
        before(() => {
            postJSONStub = sinon.stub($osf, 'postJSON', function() {
                var ret = $.Deferred();
                ret.resolve({pk : '12345'});
                return ret;
            });
            updateDataStub = sinon.stub(editor, 'updateData');
        });
        after(() => {
            $osf.postJSON.restore();
            editor.updateData.restore();
        });
        it('POSTs to the create URL with the current draft state', (done) => {

            editor.create({}).always(function() {
                assert.deepEqual(
                    postJSONStub.args[0][1].schema_data,
                    {}
                );
                done();
            });
        });
    });
    describe('#save', () => {
        var putSaveDataStub;
        beforeEach(() => {
            putSaveDataStub = sinon.stub(editor, 'putSaveData', function() {
                var ret = $.Deferred();
                ret.resolve({pk: '12345'}, 1, {});
                return ret.promise();
            });
        });
        afterEach(() => {
            editor.putSaveData.restore();
        });
        /* TODO(samchrisinger): update tests
        it('PUTs to the update URL with the current draft state', () => {
            var metaSchema = draft.metaSchema;
            questions[0].value('Updated');
            editor.save();

            var data = {};
            $.each(questions, function(i, q) {
                data[q.id] = {
                    value: q.value()
                    // comments: []
                };
            });

            assert.isTrue(
                putSaveDataStub.calledWith(
                    {
                        schema_name: metaSchema.name,
                        schema_version: metaSchema.version,
                        schema_data: data
                    }
                )
            );
        });
         */
    });
});

