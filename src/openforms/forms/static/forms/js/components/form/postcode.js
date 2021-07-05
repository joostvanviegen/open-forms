import {Formio} from "formiojs";

import DEFAULT_TABS from "./edit/tabs";
import TextField from './textfield';


class PostcodeField extends TextField {
    static schema(...extend) {
        return TextField.schema({
            label: 'Postcode',
            key: 'postcode',
            inputMask: '9999 AA',
            validateOn: 'blur',
            validate: {
              customMessage: 'Invalid Postcode'
            }
        }, ...extend);
    }

    static get builderInfo() {
        return {
            title: 'Postcode Field',
            icon: 'home',
            group: 'basic',
            weight: 10,
            schema: PostcodeField.schema(),
        };
    }

    static editForm() {
        return {components: [DEFAULT_TABS]};
    }

    get defaultSchema() {
        return PostcodeField.schema();
    }
}

export default PostcodeField;
