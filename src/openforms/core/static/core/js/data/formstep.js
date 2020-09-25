import {CrudConsumer, CrudConsumerObject} from 'consumerjs';


/**
 * A FormStep of a form.
 * @class
 */
class FormStep extends CrudConsumerObject {
}


/**
 * Consumer used for CRUD operations on FormStep objects.
 * @class
 */
export class FormStepConsumer extends CrudConsumer {
    /**
     * Constructor method.
     */
    constructor() {
        super('/api/v1/forms/', FormStep);
    }

    /**
     * Reads all FormSteps from the backend for "form".
     * @param {Form} form The Form instance to create FormStep for.
     * @param {number} stepIndex The step index.
     * @return {Promise}
     */
    read(form, stepIndex) {
        return this.get(`${form.slug}/steps/${stepIndex}`);
    }
}
