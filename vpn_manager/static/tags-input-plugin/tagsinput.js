const tagsInputElements = document.querySelectorAll('[data-role="tagsinput"]')

// Khởi tạo object lưu các mảng giá trị của tags input
tagsInputValueList = {}
tagsInputElements.forEach(input => tagsInputValueList[input.id] = [])

// Set default tags input
tagsInputValueList['client_allowed_ips'].push('0.0.0.0/0');
tagsInputValueList['client_allocated_ips'].push('10.252.1.1/32');


// Thêm sự kiện khi nhập chữ + nhấn enter trong ô input thì thêm value vào tags input
tagsInputElements.forEach(function (input) {
    input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            if (!tagsInputValueList[input.id].includes(this.value.trim())) {
                tagsInputValueList[input.id].push(this.value.trim());
                showTags(input);
            }
            this.value = '';
        }
    })

    showTags(input);
});

function removeTagItem(inputElementId, index) {
    tagsInputValueList[inputElementId].splice(index, 1)
    showTags(document.querySelector(`#${inputElementId}`));
}

function showTags(inputElement) {

    const tagsValue = inputElement.parentElement; // <ul class="tagsvalue">

    // Xoá toàn bộ thẻ <li> hiện tại
    list_tag = tagsValue.querySelectorAll('li.tag');
    list_tag.forEach(li => li.remove());

    // Thêm lại các tags input bằng <li> vào thẻ <ul>
    tagsInputValueList[inputElement.id].forEach((value, index) => {
        let newTag = createNewTagElement(value, inputElement.id, index);
        tagsValue.appendChild(newTag);

    })
}


function createNewTagElement(value, inputElementId, index) {
    let newTag = document.createElement('li');
    newTag.classList.add('tag');

    let tag_value = document.createElement('span');
    tag_value.classList.add('tag-value');
    tag_value.innerText = value;

    let remove_tag = document.createElement('span');
    remove_tag.classList.add('remove-tag', 'bi', 'bi-x-circle-fill');
    // remove_tag.innerText = 'x';
    // remove_tag.innerText = '<i class="bi bi-x-circle"></i>';

    remove_tag.addEventListener('click', function (event) {
        removeTagItem(inputElementId, index);
    })

    newTag.appendChild(tag_value);
    newTag.appendChild(remove_tag);

    return newTag;
}